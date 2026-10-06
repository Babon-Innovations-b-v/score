"""Where the picker finds candidate takes for a needed sound: a source answers a need with candidates.

Every source has the same shape (`search(need, count)` gives back `Candidate`s, `similar(candidate, count)` gives
back more like one), so a new one slots in beside these and the owner picks from it the same way: a CC0 library
now, a generated-sound source (a commercial-OK model, a paid API) later. A source only finds; fetching, trimming
and the loudness rule are the same for every candidate (takes.py).

- **Freesound**, CC0 only. With an API key (Scaleway secret `freesound-api-key`, project farm-factory; apply for
  one at https://freesound.org/apiv2/apply) it asks the API with `license:"Creative Commons 0"`; without one it
  reads the site's own search page with the same filter. Either way each candidate's licence is read again off
  its own page before it is kept, and its high-quality preview is what is fetched.
- **Kenney**, whose packs are CC0 throughout: the files of a few sound packs, matched to the need by name.
- **In the game now**: the take the game plays today, so the owner can keep it.
"""
import dataclasses
import hashlib
import html
import io
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[3]
CACHE = pathlib.Path.home() / ".cache" / "farm-factory" / "sound-picker"
AGENT = "Mozilla/5.0 (farm-factory sound picker; open-source game)"
CC0 = "CC0 1.0"
CC0_LINK = "creativecommons.org/publicdomain/zero/1.0"


@dataclasses.dataclass
class Candidate:
    """One take a source offers for a need: where it is from, who made it, under what licence, and where to fetch
    its audio."""
    source: str
    key: str
    title: str
    author: str
    licence: str
    page: str
    audio: str
    seconds: float = 0.0
    note: str = ""

    def to_json(self):
        return dataclasses.asdict(self)


## The least time between two requests to one site, in seconds, and how often a request told to slow down
## (429) is tried again: Freesound turns away a picker in a hurry.
POLITE_SECONDS = 1.2
TRIES = 6
_last_asked = {}


def fetch(url, timeout=30):
    """The bytes at a URL, asked politely: spaced out per site, and waiting when told to slow down."""
    site = urllib.parse.urlsplit(url).netloc
    for attempt in range(TRIES):
        wait = _last_asked.get(site, 0.0) + POLITE_SECONDS - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_asked[site] = time.monotonic()
        request = urllib.request.Request(url, headers={"User-Agent": AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as answer:
                return answer.read()
        except urllib.error.HTTPError as refused:
            if refused.code != 429 or attempt == TRIES - 1:
                raise
            told = refused.headers.get("Retry-After", "")
            time.sleep(float(told) if told.isdigit() else 20.0 * (attempt + 1))
    raise RuntimeError(f"picker: {url} kept refusing")


def fetch_text(url):
    """A page's text, kept in the cache: a search or a licence is read once."""
    path = CACHE / "pages" / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
    if path.exists():
        return path.read_text()
    text = fetch(url).decode("utf-8", "replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return text


def words_of(text):
    """The lower-case words in a name or a search, split at spaces, underscores, dashes and camel case."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return [word for word in re.split(r"[^a-zA-Z]+", spaced.lower()) if word]


class Freesound:
    """Freesound, CC0 only: the API with a key, the site's search page without one."""
    name = "freesound"
    SEARCH = "https://freesound.org/search/?q={query}&f=license%3A%22Creative+Commons+0%22"
    API = ("https://freesound.org/apiv2/search/text/?query={query}&filter=license:%22Creative%20Commons%200%22"
           "&fields=id,name,username,license,duration,previews,url&page_size={count}&token={key}")
    SIMILAR = "https://freesound.org/people/{author}/sounds/{key}/similar/?ajax=1"

    def __init__(self, key=None):
        self.key = key

    ## The longest recording fetched for a need of each category, in seconds: a take is cut from a short stretch
    ## of it anyway, and a long one is a slow download.
    LONGEST = {"steps": 40.0, "shot": 12.0, "loop": 120.0, "room": 180.0}

    def search(self, need, count):
        """Candidates for a need: each of its searches in turn until `count` are found."""
        found = {}
        longest = self.LONGEST.get(need["category"], 60.0)
        for query in need["search"]:
            for candidate in self._search_one(query, count * 3):
                if len(found) >= count:
                    return list(found.values())
                if candidate.seconds > longest:
                    continue
                if candidate.key not in found and self._is_cc0(candidate):
                    found[candidate.key] = candidate
        return list(found.values())

    def similar(self, candidate, count):
        """Takes Freesound finds like one: its own similar-sounds list, CC0 only."""
        listed = parse_search_page(fetch_text(self.SIMILAR.format(author=candidate.author,
                                                                  key=candidate.key.split(":")[1])))
        return [found for found in listed if self._is_cc0(found)][:count]

    def _search_one(self, query, count):
        quoted = urllib.parse.quote_plus(query)
        if self.key:
            answer = json.loads(fetch_text(self.API.format(query=quoted, count=count, key=self.key)))
            return [from_api(result) for result in answer.get("results", [])]
        return parse_search_page(fetch_text(self.SEARCH.format(query=quoted)))[:count]

    @staticmethod
    def _is_cc0(candidate):
        """Whether the sound's own page says CC0: the search filter is trusted no further than that."""
        return CC0_LINK in fetch_text(candidate.page)


def from_api(result):
    """A candidate from one result of Freesound's API."""
    return Candidate("freesound", f"freesound:{result['id']}", result["name"], result["username"], CC0,
                     result["url"], result["previews"]["preview-hq-ogg"], float(result["duration"]))


def parse_search_page(text):
    """The candidates on a Freesound search or similar-sounds page, in its order, with their high-quality previews."""
    found = []
    for block in re.finditer(r'class="bw-player"(.*?)tabindex', text, re.S):
        fields = dict(re.findall(r'data-([a-z-]+)="([^"]*)"', block.group(1)))
        if "sound-id" not in fields or "ogg" not in fields:
            continue
        key, author = fields["sound-id"], fields.get("username", "")
        found.append(Candidate("freesound", f"freesound:{key}", html.unescape(fields.get("title", key)),
                               author, CC0, f"https://freesound.org/people/{author}/sounds/{key}/",
                               fields["ogg"].replace("-lq.ogg", "-hq.ogg"), float(fields.get("duration", 0) or 0)))
    return found


class Kenney:
    """Kenney's sound packs, every file CC0: matched to a need by the words of its file names."""
    name = "kenney"
    PACKS = ("impact-sounds", "sci-fi-sounds", "interface-sounds")
    PAGE = "https://kenney.nl/assets/{pack}"
    ## A file is a candidate when this many of a need's search words are in its name.
    MATCHED_WORDS = 2

    def search(self, need, count):
        wanted = {word for query in need["search"] for word in words_of(query)}
        scored = []
        for pack in self.PACKS:
            for member, path in self._pack_files(pack).items():
                score = len(wanted & set(words_of(pathlib.Path(member).stem)))
                if score >= self.MATCHED_WORDS:
                    scored.append((-score, member, pack, path))
        scored.sort()
        return [Candidate("kenney", f"kenney:{pack}/{pathlib.Path(member).name}", pathlib.Path(member).stem,
                          "Kenney", CC0, self.PAGE.format(pack=pack), path.as_uri())
                for _, member, pack, path in scored[:count]]

    def similar(self, candidate, count):
        return []

    def _pack_files(self, pack):
        """A pack's audio files, unpacked into the cache once, by their name in the pack."""
        folder = CACHE / "kenney" / pack
        if not folder.exists():
            link = re.search(r'https://kenney\.nl/media/pages/assets/[^"]*\.zip', fetch_text(self.PAGE.format(pack=pack)))
            if not link:
                raise RuntimeError(f"picker: Kenney's {pack} page names no zip")
            folder.mkdir(parents=True)
            zipfile.ZipFile(io.BytesIO(fetch(link.group(0), timeout=120))).extractall(folder)
        licence = folder / "License.txt"
        if not licence.exists() or CC0_LINK not in licence.read_text(errors="replace"):
            raise RuntimeError(f"picker: Kenney's {pack} does not say CC0 in its License.txt")
        return {str(path.relative_to(folder)): path for path in folder.rglob("*.ogg")}


class InTheGame:
    """The take the game plays today for a sound already picked, so keeping it is one of the choices."""
    name = "game"

    def __init__(self, licences, current_files):
        self.licences = licences
        self.current_files = current_files

    def search(self, need, count):
        found = []
        for res_path in self.current_files(need["name"])[:1]:
            listed = self.licences.get(res_path, {})
            local = REPO / res_path.removeprefix("res://")
            found.append(Candidate("game", f"game:{need['name']}", f"in the game now ({local.name})",
                                   listed.get("author", "?"), listed.get("licence", "?"), listed.get("source", ""),
                                   local.as_uri(), note="the take the game plays today"))
        return found

    def similar(self, candidate, count):
        return []


def freesound_key():
    """The Freesound API key from Scaleway's Secret Manager, or None when there is none yet."""
    sys.path.insert(0, str(REPO / "tools" / "props" / "cloud"))
    import scaleway  # noqa: E402  (the one place secrets are read)
    try:
        return scaleway.secret("freesound-api-key")
    except Exception as missing:  # the secret not made yet is the usual case, said and not hidden
        print(f"picker: no Freesound API key ({type(missing).__name__}); reading the site's CC0 search instead")
        return None

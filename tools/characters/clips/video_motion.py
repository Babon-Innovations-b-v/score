"""A body's motion read off a video, on the rented card (tools/cloud/characters.py runs it for a make folder
whose spec names "program": "video_motion.py"; never on the owner's PC):

    /root/envs/motion/bin/python video_motion.py /root/make/<name>

SAM 3D Body reads the person in every frame of the spec's `files.video` (sam3dbody-cpp's offline multi-pass
extractor, `scripts/offline_video.sh`, its zero-phase smoothing and tracker), written as one BVH a tracked person
on its MHR-rest template (bvh/body_mhr.bvh). The person seen in the most frames is kept as out/clip.bvh; the
retarget onto the people's rig runs back on the store's machine (retarget.py). The record is out/make.json, written
by the maker's step runner (../maker/chain.py).
"""
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "maker"))

import chain as person_chain  # noqa: E402

ENGINE = pathlib.Path("/root/sam3dbody-cpp")  # body_picture.py's: characters_setup.sh builds it there


def frames_of(bvh):
    """The frame count a BVH file's MOTION block names."""
    for line in bvh.read_text().splitlines():
        if line.startswith("Frames:"):
            return int(line.split()[1])
    return 0


def read(chain):
    """Step `video`: every tracked person's BVH, the one seen longest copied to out/clip.bvh."""
    work = chain.work / "bvh"
    work.mkdir(exist_ok=True)
    chain.run(["bash", ENGINE / "scripts/offline_video.sh", "--from", chain.file(chain.spec["files"]["video"]),
               "--bvh", work / "person.bvh"])
    people = sorted(work.glob("person_*.bvh"), key=frames_of)
    if not people:
        raise RuntimeError("SAM 3D Body found nobody in the video")
    shutil.copy2(people[-1], chain.out / "clip.bvh")
    return f"{len(people)} people tracked; kept {people[-1].name}, {frames_of(people[-1])} frames"


def main():
    chain = person_chain.Chain(pathlib.Path(sys.argv[1]))
    chain.step("video", lambda: read(chain))
    print(f"read {chain.spec['name']} in {chain.record['minutes']} min", flush=True)


if __name__ == "__main__":
    main()

# score/stages/video_clips/

The video clip rows (experimental, #52; CONTEXT.md "video clip"; `__init__.py`'s docstring has the make, the gates
and the price). Each video the creator uploads to `{home}/design/clips/<clip>.mp4` gets one paid environment row,
`video-clip-<clip>`. The row reads the video with SAM 3D Body on a rented characters machine and retargets the motion
onto the rig of `people-clips-made` (`tools/characters/clips`, its overlay). The result is a rig clip in the same
form as the rig's own Kimodo `clip_<name>`. The video is copied into the output, so the store keeps it.

- **No row without a video.** `rows()` reads the folder, so an environment without an uploaded video gets no row.
- **No measured price.** `EUROS` is a guess that the runner keeps apart. Replace it once a run is measured.
- **Not yet played by a body.** A person row cannot name a video clip yet. Its clip is
  `people_rows.doing_of`, and that module is read by the paid rows people-clips-made, the bodies, sound and
  demo-film, so editing it re-keys all of them. Two steps are still to do: a row's `clip` naming
  `video-clip-<clip>`, and the clip's frames added to the rig as `clip_<clip>`. That re-keying is the owner's call
  (#52).
- Tests: `test_a_row_per_upload_and_gates_refuse_flips.py` covers the rows and the gates on a toy clip.

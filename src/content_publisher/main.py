#!/usr/bin/env python3

import logging

from app.app import App
from app.content_publisher import Content
from app.run_arg import RunArg

if __name__ == "__main__":
    run_args = RunArg.of_sys_argv()
    logging.basicConfig(
        level=logging.DEBUG if run_args.get(RunArg.VERBOSE) is True else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    platforms = run_args.get(RunArg.PLATFORMS)
    print(f"Publishing to platforms: `{platforms}`")
    dir_path = run_args.get(RunArg.DIR)
    text_title = run_args.get(RunArg.TEXT_TITLE)
    media_orientation = run_args.get(RunArg.MEDIA_ORIENTATION)
    language_code = run_args.get(RunArg.LANGUAGE_CODE)
    tags = run_args.get(RunArg.TAGS)

    content = Content.of_dir(dir_path, title=text_title, media_orientation=media_orientation,
                             language_code=language_code, tags=tags)

    configs = {
        "youtube": {
            "dry_run": True,
            "credentials_filename": "youtube-expired.pickle"
        },
        "facebook": {
            "dry_run": True,
            "credentials_scopes": ['business_management', 'pages_show_list']
        },
        "tiktok": {
            "dry_run": True,
            "callback_path": '/callback',
            # TODO - Remove this post_info, when we are able to post to TikTok
            #  with privacy PUBLIC TO EVERYONE (i.e the default)
            "post_info": {
                "language": content.language_code or 'en',
                "privacy_level": 'SELF_ONLY',
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 250
            }
        }
    }

    App().publish_content(platforms, content, configs)
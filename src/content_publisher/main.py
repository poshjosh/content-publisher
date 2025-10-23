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
    dir_path = run_args.get(RunArg.DIR)
    text_title = run_args.get(RunArg.TEXT_TITLE)
    media_orientation = run_args.get(RunArg.MEDIA_ORIENTATION)
    language_code = run_args.get(RunArg.LANGUAGE_CODE)
    tags = run_args.get(RunArg.TAGS)

    content = Content.of_dir(dir_path, text_title, media_orientation, language_code, tags)

    App().publish_content(platforms, content)
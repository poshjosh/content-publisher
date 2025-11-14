# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.12] - 2025-11-14

### Added

- Allow specifying of media_orientation as content metadata, use it to configure YouTube shorts.
- Fix bug which occurs due to trying to fresh invalid oauth token.
- Fix bug in processing of oauth credentials expiry.
- Fix bug in handling of YouTube tags.
- Allow users specify whether to add thumbnail or subtitles to YouTube video posts.

## [0.0.11] - 2025-11-03

### Fixed

- Fixed saving of credentials bug, which occurs with filename having leading slash.

## [0.0.10] - 2025-11-02

### Added

- Allow for customizing posts
- truncate content based on platform length restriction

## [0.0.9] - 2025-11-01

### Added

- Customizations for credentials filename and scopes.
- Facebook content publisher.
- X/Twitter content publisher.

## [0.0.8] - 2025-10-26

### Added

- TikTok content publisher.
- Approval of reddit post.

### Changed

- Save oauth tokens to `~/.content-publisher/oauth-tokens/`

## [0.0.7] - 2025-10-25

- Validate length of tags

## [0.0.6] - 2025-10-23

- Added run args `tags` and `language-code`.

## [0.0.5] - 2025-10-12

- Implement posting to Reddit.

## [0.0.4] - 2025-10-10

- Improve implementation of `RunArg`.

## [0.0.3] - 2025-10-09

- Rename package of main entrypoint

## [0.0.2] - 2025-10-09

- Use pyproject.toml

## [0.0.1] - 2025-10-09

### Added

- Initial commit

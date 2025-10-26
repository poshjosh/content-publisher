Write python classes/code for posting content to TikTok.

Given: 

- a `str` api endpoint URL.
- a `Dict` containing tiktok client key and secret.
- a `Content` object with the following attributes/properties:

```python
@dataclass
class Content:
    description: str
    video_file: Optional[str] = None
    image_file: Optional[str] = None
    title: Optional[str] = None
    language_code: Optional[str] = None
    tags: Optional[List[str]] = None
```

Does the following:

- authenticates with the TikTok API using the provided client key and secret.
- uploads the content (video or image) to TikTok with the provided description, title, language code, and tags (as applicable).
- handles errors and exceptions that may occur during the process.

References:

You may (or may not) refer to the following TikTok API documentation for details: 

- https://developers.tiktok.com/doc/oauth-user-access-token-management
- https://developers.tiktok.com/doc/login-kit-manage-user-access-tokens
- https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content/
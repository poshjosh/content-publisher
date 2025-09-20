Write a python program for posting content to social media which,

Given an object with the following attributes/properties:

*	A social media platform name e.g. YouTube, Meta (Facebook), TikTok, Instagram, x (Twitter), Reddit.
*	An API endpoint for the social media platform.
*	API credentials
*	A content object comprising the following:
    ** A content video file (optional)
    ** A content image file (optional)
    ** A content title (optional)
    ** A content description
    ** Content subtitle files for multiple languages (optional)
    
Does the following:

*	Using the social media platform name selects an appropriate handler for posting content to the social media platform.
*	If the named social media platform does not have an API, returns a result object.
*	Publishes the provided content to the named social media platform.
*	Adds subtitles to the content only if the named social media platform supports subtitles.
*	Returns a result object with:
    ** A flag denoting either success or failure.
    ** A detailed result message.
    ** A log/trace of steps which were successful e.g. content valid, selected handler, published content, added subtitles.

from content_publisher import Content
import unittest


class ContentTest(unittest.TestCase):
    """Unit tests for extract_hashtags_from_text function"""

    # ========================================================================
    # Basic Functionality Tests
    # ========================================================================

    def test_single_hashtag(self):
        """Test extraction of a single hashtag"""
        result = Content.extract_hashtags_from_text("#python", 10)
        self.assertEqual(result, ["python"])

    def test_multiple_hashtags(self):
        """Test extraction of multiple hashtags"""
        result = Content.extract_hashtags_from_text("#python #java #rust", 20)
        self.assertEqual(result, ["python", "java", "rust"])

    def test_no_hashtags(self):
        """Test text without any hashtags"""
        result = Content.extract_hashtags_from_text("This is plain text", 100)
        self.assertEqual(result, [])

    def test_empty_string(self):
        """Test empty string input"""
        result = Content.extract_hashtags_from_text("", 100)
        self.assertEqual(result, [])

    def test_hashtag_at_start(self):
        """Test hashtag at the beginning of text"""
        result = Content.extract_hashtags_from_text("#start of text", 10)
        self.assertEqual(result, ["start"])

    def test_hashtag_at_end(self):
        """Test hashtag at the end of text"""
        result = Content.extract_hashtags_from_text("end of text #end", 10)
        self.assertEqual(result, ["end"])

    def test_hashtag_in_middle(self):
        """Test hashtag in the middle of text"""
        result = Content.extract_hashtags_from_text("some #middle text", 10)
        self.assertEqual(result, ["middle"])

    def test_that_hashtags_with_spaces_are_not_extracted(self):
        """Test that hashtags with spaces are not extracted"""
        result = Content.extract_hashtags_from_text("#python programming #java code", 30)
        self.assertEqual(result, ["python", "java"])

    # ========================================================================
    # Max Length Tests
    # ========================================================================

    def test_max_length_exact_fit(self):
        """Test when total length exactly matches max_tags_length"""
        # "python" = 6 chars, no comma for first tag
        result = Content.extract_hashtags_from_text("#python", 6)
        self.assertEqual(result, ["python"])

    def test_max_length_exact_fit_two_tags(self):
        """Test when two tags exactly fit max_tags_length"""
        # "python" (6) + comma (1) + "java" (4) = 11
        result = Content.extract_hashtags_from_text("#python #java", 11)
        self.assertEqual(result, ["python", "java"])

    def test_max_length_one_char_short(self):
        """Test when second tag is one char too long"""
        # "python" (6) + comma (1) + "java" (4) = 11, but max is 10
        result = Content.extract_hashtags_from_text("#python #java", 10)
        self.assertEqual(result, ["python"])

    def test_max_length_zero(self):
        """Test with max_tags_length of 0"""
        result = Content.extract_hashtags_from_text("#python #java", 0)
        self.assertEqual(result, [])

    def test_max_length_one(self):
        """Test with max_tags_length of 1"""
        result = Content.extract_hashtags_from_text("#a #b", 1)
        self.assertEqual(result, ["a"])

    def test_max_length_excludes_all_tags(self):
        """Test when max_tags_length is too small for any tag"""
        result = Content.extract_hashtags_from_text("#python #java", 3)
        self.assertEqual(result, [])

    def test_max_length_allows_first_only(self):
        """Test when only first tag fits"""
        result = Content.extract_hashtags_from_text("#hi #verylongtag", 5)
        self.assertEqual(result, ["hi"])

    def test_max_length_very_large(self):
        """Test with very large max_tags_length"""
        result = Content.extract_hashtags_from_text("#a #b #c", 10000)
        self.assertEqual(result, ["a", "b", "c"])

    def test_max_length_negative(self):
        """Test with negative max_tags_length"""
        result = Content.extract_hashtags_from_text("#python", -1)
        self.assertEqual(result, [])

    def test_progressive_length_limit(self):
        """Test that tags are added until length limit is reached"""
        # "a" (1) + "," (1) + "b" (1) + "," (1) + "c" (1) = 5
        # With max=3: only "a,b" fits (1 + 1 + 1 = 3)
        result = Content.extract_hashtags_from_text("#a #b #c #d", 3)
        self.assertEqual(result, ["a", "b"])

    # ========================================================================
    # Hashtag Format Tests
    # ========================================================================

    def test_hashtag_with_numbers(self):
        """Test hashtags containing numbers"""
        result = Content.extract_hashtags_from_text("#python3 #java8", 20)
        self.assertEqual(result, ["python3", "java8"])

    def test_hashtag_with_underscore(self):
        """Test hashtags containing underscores"""
        result = Content.extract_hashtags_from_text("#python_lang #java_script", 30)
        self.assertEqual(result, ["python_lang", "java_script"])

    def test_hashtag_all_numbers(self):
        """Test hashtag that is all numbers"""
        result = Content.extract_hashtags_from_text("#123 #456", 10)
        self.assertEqual(result, ["123", "456"])

    def test_hashtag_mixed_case(self):
        """Test hashtags with mixed case"""
        result = Content.extract_hashtags_from_text("#Python #JAVA #RuSt", 20)
        self.assertEqual(result, ["Python", "JAVA", "RuSt"])

    def test_hashtag_only_underscore(self):
        """Test hashtag that is only underscore"""
        result = Content.extract_hashtags_from_text("#_ #__ #___", 10)
        self.assertEqual(result, ["_", "__", "___"])

    def test_consecutive_hashtags_no_space(self):
        """Test consecutive hashtags without spaces"""
        result = Content.extract_hashtags_from_text("#python#java#rust", 20)
        self.assertEqual(result, ["python", "java", "rust"])

    def test_hashtag_at_word_boundary(self):
        """Test hashtags separated by various characters"""
        result = Content.extract_hashtags_from_text("#python.#java,#rust;#go", 20)
        self.assertEqual(result, ["python", "java", "rust", "go"])

    # ========================================================================
    # Special Characters and Edge Cases
    # ========================================================================

    def test_hashtag_with_special_chars_after(self):
        """Test hashtag followed by special characters (not included)"""
        result = Content.extract_hashtags_from_text("#python! #java? #rust.", 20)
        self.assertEqual(result, ["python", "java", "rust"])

    def test_hashtag_with_hyphen_breaks(self):
        """Test that hyphen breaks hashtag extraction"""
        result = Content.extract_hashtags_from_text("#python-lang", 20)
        self.assertEqual(result, ["python"])

    def test_hashtag_with_space_breaks(self):
        """Test that space breaks hashtag extraction"""
        result = Content.extract_hashtags_from_text("#python lang", 20)
        self.assertEqual(result, ["python"])

    def test_double_hash(self):
        """Test double hash symbols"""
        result = Content.extract_hashtags_from_text("##python", 20)
        self.assertEqual(result, ["python"])

    def test_hash_only(self):
        """Test hash symbol without following word characters"""
        result = Content.extract_hashtags_from_text("# # #", 20)
        self.assertEqual(result, [])

    def test_hash_with_emoji(self):
        """Test hash with emoji (emoji not captured by \\w)"""
        result = Content.extract_hashtags_from_text("#python🐍 #java☕", 20)
        self.assertEqual(result, ["python", "java"])

    def test_unicode_letters(self):
        """Test hashtags with unicode letters (if \\w supports them)"""
        # Note: \\w in Python includes Unicode letters
        result = Content.extract_hashtags_from_text("#café #münchen", 20)
        self.assertEqual(result, ["café", "münchen"])

    def test_hashtag_in_url(self):
        """Test hashtag within URL"""
        result = Content.extract_hashtags_from_text("https://example.com#section #python", 20)
        self.assertEqual(result, ["section", "python"])

    # ========================================================================
    # Whitespace Tests
    # ========================================================================

    def test_multiple_spaces_between_hashtags(self):
        """Test multiple spaces between hashtags"""
        result = Content.extract_hashtags_from_text("#python    #java     #rust", 20)
        self.assertEqual(result, ["python", "java", "rust"])

    def test_tabs_between_hashtags(self):
        """Test tabs between hashtags"""
        result = Content.extract_hashtags_from_text("#python\t#java\t#rust", 20)
        self.assertEqual(result, ["python", "java", "rust"])

    def test_newlines_between_hashtags(self):
        """Test newlines between hashtags"""
        result = Content.extract_hashtags_from_text("#python\n#java\n#rust", 20)
        self.assertEqual(result, ["python", "java", "rust"])

    def test_mixed_whitespace(self):
        """Test mixed whitespace characters"""
        result = Content.extract_hashtags_from_text("#python \t\n #java", 20)
        self.assertEqual(result, ["python", "java"])

    def test_leading_whitespace(self):
        """Test text with leading whitespace"""
        result = Content.extract_hashtags_from_text("   #python #java", 20)
        self.assertEqual(result, ["python", "java"])

    def test_trailing_whitespace(self):
        """Test text with trailing whitespace"""
        result = Content.extract_hashtags_from_text("#python #java   ", 20)
        self.assertEqual(result, ["python", "java"])

    # ========================================================================
    # Duplicate Hashtags Tests
    # ========================================================================

    def test_duplicate_hashtags(self):
        """Test that duplicate hashtags are included multiple times"""
        result = Content.extract_hashtags_from_text("#python #java #python", 20)
        self.assertEqual(result, ["python", "java", "python"])

    def test_duplicate_hashtags_case_sensitive(self):
        """Test that duplicates with different cases are treated separately"""
        result = Content.extract_hashtags_from_text("#Python #python #PYTHON", 20)
        self.assertEqual(result, ["Python", "python", "PYTHON"])

    def test_many_duplicates(self):
        """Test with many duplicate hashtags"""
        result = Content.extract_hashtags_from_text("#a #a #a #a #a", 20)
        self.assertEqual(result, ["a", "a", "a", "a", "a"])

    # ========================================================================
    # Complex Text Tests
    # ========================================================================

    def test_hashtags_in_sentence(self):
        """Test hashtags within a sentence"""
        text = "I love #python and #java for #coding tasks"
        result = Content.extract_hashtags_from_text(text, 25)
        self.assertEqual(result, ["python", "java", "coding"])

    def test_hashtags_with_punctuation(self):
        """Test hashtags mixed with punctuation"""
        text = "Check out #python! Also, try #java. Finally, #rust?"
        result = Content.extract_hashtags_from_text(text, 25)
        self.assertEqual(result, ["python", "java", "rust"])

    def test_social_media_post(self):
        """Test realistic social media post with multiple hashtags"""
        text = "Just finished my #python project! 🎉 #coding #webdev #opensource"
        result = Content.extract_hashtags_from_text(text, 20)
        self.assertEqual(result, ["python", "coding", "webdev"])

    def test_hashtags_in_markdown(self):
        """Test hashtags in markdown-like text"""
        text = "# Header\n\nSome text with #python and #java"
        result = Content.extract_hashtags_from_text(text, 20)
        self.assertEqual(result, ["python", "java"])

    def test_very_long_text(self):
        """Test with very long text containing multiple hashtags"""
        text = "word " * 1000 + "#python " + "word " * 1000 + "#java"
        result = Content.extract_hashtags_from_text(text, 20)
        self.assertEqual(result, ["python", "java"])

    # ========================================================================
    # Length Calculation Tests
    # ========================================================================

    def test_comma_calculation_first_tag(self):
        """Test that first tag doesn't include comma in length"""
        # "python" = 6 chars (no comma for first)
        result = Content.extract_hashtags_from_text("#python", 6)
        self.assertEqual(result, ["python"])

        # Should fail at 5
        result = Content.extract_hashtags_from_text("#python", 5)
        self.assertEqual(result, [])

    def test_comma_calculation_second_tag(self):
        """Test that second tag includes comma in length"""
        # "a" (1) + comma (1) + "b" (1) = 3
        result = Content.extract_hashtags_from_text("#a #b", 3)
        self.assertEqual(result, ["a", "b"])

        # Should only include first tag at 2
        result = Content.extract_hashtags_from_text("#a #b", 2)
        self.assertEqual(result, ["a"])

    def test_comma_calculation_multiple_tags(self):
        """Test comma calculation with multiple tags"""
        # "a" (1) + "," (1) + "b" (1) + "," (1) + "c" (1) = 5
        result = Content.extract_hashtags_from_text("#a #b #c", 5)
        self.assertEqual(result, ["a", "b", "c"])

        # At 4, should only get first two
        result = Content.extract_hashtags_from_text("#a #b #c", 4)
        self.assertEqual(result, ["a", "b"])

    def test_varying_tag_lengths(self):
        """Test with tags of varying lengths"""
        # "hi" (2) + "," (1) + "hello" (5) + "," (1) + "hey" (3) = 12
        result = Content.extract_hashtags_from_text("#hi #hello #hey", 12)
        self.assertEqual(result, ["hi", "hello", "hey"])

    # ========================================================================
    # Order Preservation Tests
    # ========================================================================

    def test_order_preserved(self):
        """Test that hashtag order is preserved"""
        result = Content.extract_hashtags_from_text("#first #second #third", 30)
        self.assertEqual(result, ["first", "second", "third"])

    def test_order_preserved_with_limit(self):
        """Test order is preserved when hitting length limit"""
        result = Content.extract_hashtags_from_text("#z #y #x #w", 5)
        self.assertEqual(result, ["z", "y", "x"])

    # ========================================================================
    # Single Character Tests
    # ========================================================================

    def test_single_char_hashtags(self):
        """Test single character hashtags"""
        result = Content.extract_hashtags_from_text("#a #b #c #d", 10)
        self.assertEqual(result, ["a", "b", "c", "d"])

    def test_single_char_with_numbers(self):
        """Test single character and number hashtags"""
        result = Content.extract_hashtags_from_text("#1 #2 #3 #a #b", 10)
        self.assertEqual(result, ["1", "2", "3", "a", "b"])

    # ========================================================================
    # Return Type Tests
    # ========================================================================

    def test_return_type_is_list(self):
        """Test that return type is a list"""
        result = Content.extract_hashtags_from_text("#python", 10)
        self.assertIsInstance(result, list)

    def test_return_elements_are_strings(self):
        """Test that all returned elements are strings"""
        result = Content.extract_hashtags_from_text("#python #java #rust", 20)
        for tag in result:
            self.assertIsInstance(tag, str)

    def test_returned_tags_have_no_hash(self):
        """Test that returned tags don't have hash symbols"""
        result = Content.extract_hashtags_from_text("#python #java", 20)
        for tag in result:
            self.assertFalse(tag.startswith('#'))

    # ========================================================================
    # Boundary Value Tests
    # ========================================================================

    def test_max_length_boundary_values(self):
        """Test various boundary values for max_tags_length"""
        text = "#a #bb #ccc"

        # Test incrementing max_tags_length
        self.assertEqual(Content.extract_hashtags_from_text(text, 0), [])
        self.assertEqual(Content.extract_hashtags_from_text(text, 1), ["a"])
        self.assertEqual(Content.extract_hashtags_from_text(text, 2), ["a"])
        self.assertEqual(Content.extract_hashtags_from_text(text, 3), ["a"])
        self.assertEqual(Content.extract_hashtags_from_text(text, 4), ["a", "bb"])
        self.assertEqual(Content.extract_hashtags_from_text(text, 5), ["a", "bb"])
        self.assertEqual(Content.extract_hashtags_from_text(text, 9), ["a", "bb", "ccc"])

    def test_very_long_hashtag(self):
        """Test with a very long hashtag"""
        long_tag = "a" * 1000
        result = Content.extract_hashtags_from_text(f"#{long_tag}", 500)
        self.assertEqual(result, [])

        result = Content.extract_hashtags_from_text(f"#{long_tag}", 1000)
        self.assertEqual(result, [long_tag])

    def test_many_short_hashtags(self):
        """Test with many short hashtags"""
        text = " ".join([f"#a{i}" for i in range(100)])
        result = Content.extract_hashtags_from_text(text, 1000)
        self.assertEqual(len(result), 100)

    # ========================================================================
    # Empty and None-like Tests
    # ========================================================================

    def test_whitespace_only(self):
        """Test string with only whitespace"""
        result = Content.extract_hashtags_from_text("   \t\n   ", 10)
        self.assertEqual(result, [])

    def test_hash_with_no_word_chars(self):
        """Test hash symbol followed by non-word characters"""
        result = Content.extract_hashtags_from_text("#! #@ #$ #%", 10)
        self.assertEqual(result, [])

    def test_text_with_no_valid_hashtags(self):
        """Test text that looks like it has hashtags but doesn't"""
        result = Content.extract_hashtags_from_text("# tag # another # test", 20)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
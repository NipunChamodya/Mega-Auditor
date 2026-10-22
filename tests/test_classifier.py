import unittest
from mega_auditor.classifier import classify

class ClassifierTests(unittest.TestCase):
    def test_java_course_is_learning(self):
        result = classify({"name": "Java Beginner Course", "sources": ["links.txt"], "preview": []})
        self.assertTrue(result["is_learning_material"])
        self.assertTrue(result["primary_category"].startswith("learning/"))
    def test_movie_not_learning(self):
        result = classify({"name": "Java Movie Collection 1080p.mkv", "sources": [], "preview": []})
        self.assertFalse(result["is_learning_material"])
        self.assertTrue(result["primary_category"].startswith("non_learning/"))
    def test_ambiguous_name_needs_review(self):
        result = classify({"name": "Lecture_05.mp4", "sources": [], "preview": []})
        self.assertTrue(result["review_required"])
    def test_source_path_can_provide_context(self):
        result = classify({"name": "module.pdf", "sources": ["/uni/Java Programming Course/module.pdf"], "preview": []})
        self.assertTrue(result["is_learning_material"])

if __name__ == "__main__": unittest.main()

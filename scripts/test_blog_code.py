import ast
import unittest

from bs4 import BeautifulSoup

from blog_code import NBSP, repair_python_spaces


class PythonExamplesTest(unittest.TestCase):
    def test_rich_text_preserves_literals_comments_and_highlighting(self):
        markup = (
            '<pre><code><span>def</span>~example():<br>'
            '~~~~value~=~"""first~line<br>second~line"""<br>'
            '~~~~return~value~~# keep~this</code></pre>'
        ).replace("~", NBSP)
        pre = BeautifulSoup(markup, "lxml").pre
        repair_python_spaces(pre)
        self.assertEqual(pre.span.string, "def")
        once = str(pre)
        repair_python_spaces(pre)
        self.assertEqual(str(pre), once)
        for br in pre.find_all("br"):
            br.replace_with("\n")
        source = pre.get_text()
        ast.parse(source)
        self.assertIn(f'"""first{NBSP}line\nsecond{NBSP}line"""', source)
        self.assertIn(f"# keep{NBSP}this", source)

    def test_numbered_and_highlighted_lines(self):
        for markup in (
            '<pre><span class="line">def~f():</span><span class="line">~~pass</span></pre>',
            '<pre><ol class="linenums"><li>def~f():</li><li><span class="linenum">2</span>~~pass</li></ol></pre>',
        ):
            with self.subTest(markup=markup):
                pre = BeautifulSoup(markup.replace("~", NBSP), "lxml").pre
                repair_python_spaces(pre)
                self.assertNotIn(NBSP, pre.get_text())

    def test_other_languages_and_prose_are_unchanged(self):
        for markup in ('<pre><code class="language-js">if~true: pass</code></pre>',
                       '<pre>plain~text</pre>'):
            pre = BeautifulSoup(markup.replace("~", NBSP), "lxml").pre
            original = str(pre)
            repair_python_spaces(pre)
            self.assertEqual(str(pre), original)

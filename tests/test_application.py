import pytest
import json
import markdown
from mock import patch, mock_open
from gwbridge import application


@pytest.fixture(scope="module")
def mock_md_file():

    md = "# This is the heading of the post\n\n## This is the second heading\n\nThis is what content looks like. I really like it! This is a code block for a bash terminal:\n\n```bash\n$ which pandoc\n```\n\nThis has the following advantages:\n\n1. First advantage\n2. Second\n3. Third\n\n- list item 1\n- list item 2\n- list item 3\n\nAnd this is a code block for some python code:\n\n```python\nfrom abc import ABC\nfrom abc import abstractmethod\nimport tzlocal\nimport pytz\nimport sys\n\n\nclass Notifier(ABC):\n    def __init__():\n        self.__config = config\n        self.__creds = creds\n        self._db = db\n        self._tz = pytz.timezone(timezone)\n        self._thresh = fileio.import_json(self.__config)\n```\n\n\n### Heading 3\n\nThis is a sub sub heading. This is where more granular detail goes. Lets see if we can _italic_ and **bold** some text. This is some `pre formatted` text! It's great.\n\nLets also test an image! This is an image:\n\n![](img/test.png)\n\nThis is another image:\n\n![](img/another_image.jpg)\n"
    yield md


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data=json.dumps(
        {
            "base_url": "https://www.example.com/wp-json",
            "api_version": "wp/v2",
            "file": "README.md",
        }
    ),
)
@patch("os.path.exists")
def test_parse_args(mock_os, mock_file):
    """This test shows that parameters read from a file and passed as an
    argument will be aggregated together, and the command line arguments
    will take priority"
    """
    mock_os.return_value = True
    args = {
        "file": "test.md",
        "client_key": "wwww",
        "client_secret": "xxxx",
        "resource_owner_key": "yyyy",
        "resource_owner_secret": "zzzz",
    }

    config = application.parse_args(**args)
    print(config)

    assert config
    assert config.get("file") == "test.md"
    assert config.get("client_key") == "wwww"
    assert config.get("client_secret") == "xxxx"
    assert config.get("resource_owner_key") == "yyyy"
    assert config.get("resource_owner_secret") == "zzzz"
    assert config.get("base_url") == "https://www.example.com/wp-json"
    assert config.get("api_version") == "wp/v2"


def test_parse_document(mock_md_file):
    payload = application.parse_document(mock_md_file)

    assert payload.get("title") == "This is the heading of the post"
    comparison = '<h2 id="this-is-the-second-heading">\n This is the second heading\n</h2>\n<p>\n This is what content looks like. I really like it! This is a code block for a bash terminal:\n</p>\n<div class="sourceCode" id="cb1">\n <pre class="sourceCode bash"><code class="sourceCode bash"><span id="cb1-1"><a href="#cb1-1"></a>$ <span class="fu">which</span> pandoc</span></code></pre>\n</div>\n<p>\n This has the following advantages:\n</p>\n<ol type="1">\n <li>\n  First advantage\n </li>\n <li>\n  Second\n </li>\n <li>\n  Third\n </li>\n</ol>\n<ul>\n <li>\n  list item 1\n </li>\n <li>\n  list item 2\n </li>\n <li>\n  list item 3\n </li>\n</ul>\n<p>\n And this is a code block for some python code:\n</p>\n<div class="sourceCode" id="cb2">\n <pre class="sourceCode python"><code class="sourceCode python"><span id="cb2-1"><a href="#cb2-1"></a><span class="im">from</span> abc <span class="im">import</span> ABC</span>\n<span id="cb2-2"><a href="#cb2-2"></a><span class="im">from</span> abc <span class="im">import</span> abstractmethod</span>\n<span id="cb2-3"><a href="#cb2-3"></a><span class="im">import</span> tzlocal</span>\n<span id="cb2-4"><a href="#cb2-4"></a><span class="im">import</span> pytz</span>\n<span id="cb2-5"><a href="#cb2-5"></a><span class="im">import</span> sys</span>\n<span id="cb2-6"><a href="#cb2-6"></a></span>\n<span id="cb2-7"><a href="#cb2-7"></a></span>\n<span id="cb2-8"><a href="#cb2-8"></a><span class="kw">class</span> Notifier(ABC):</span>\n<span id="cb2-9"><a href="#cb2-9"></a>    <span class="kw">def</span> <span class="fu">__init__</span>():</span>\n<span id="cb2-10"><a href="#cb2-10"></a>        <span class="va">self</span>.__config <span class="op">=</span> config</span>\n<span id="cb2-11"><a href="#cb2-11"></a>        <span class="va">self</span>.__creds <span class="op">=</span> creds</span>\n<span id="cb2-12"><a href="#cb2-12"></a>        <span class="va">self</span>._db <span class="op">=</span> db</span>\n<span id="cb2-13"><a href="#cb2-13"></a>        <span class="va">self</span>._tz <span class="op">=</span> pytz.timezone(timezone)</span>\n<span id="cb2-14"><a href="#cb2-14"></a>        <span class="va">self</span>._thresh <span class="op">=</span> fileio.import_json(<span class="va">self</span>.__config)</span></code></pre>\n</div>\n<h3 id="heading-3">\n Heading 3\n</h3>\n<p>\n This is a sub sub heading. This is where more granular detail goes. Lets see if we can\n <em>\n  italic\n </em>\n and\n <strong>\n  bold\n </strong>\n some text. This is some\n <code>\n  pre formatted\n </code>\n text! It&rsquo;s great.\n</p>\n<p>\n Lets also test an image! This is an image:\n</p>\n<p>\n <img src="img/test.png">\n</p>\n<p>\n This is another image:\n</p>\n<p>\n <img src="img/another_image.jpg">\n</p>\n'
    assert payload.get("content") == comparison

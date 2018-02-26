import re
import reprlib
import tempfile
import webbrowser

from Tw5Mixin import Tw5Mixin
import pypandoc


class Tiddler(Tw5Mixin):

    RE_TIDDLER = re.compile('<div'
                            '(?P<options>[\w\W]*?)'
                            '>\n'
                            '<pre>'
                            '(?P<content>[\w\W]*?)</pre>\n'
                            '</div>')

    RE_OPTION = re.compile('\s+(?P<key>\w+?)=\"(?P<value>[\w\W]*?)\"')

    def __init__(self, content, title=None, tags=None, created=None, modified=None,
                 type='text/vnd.tiddlywiki', **kwargs):
        self.content = content
        self.title = title
        self.tags = [] if tags is None else tags
        self.created = created
        self.modified = modified
        self.type_ = type
        self.__dict__.update(kwargs)

    @classmethod
    def finditer(cls, buffer):

        for match in re.finditer(cls.RE_TIDDLER, buffer):
            options = match.group('options')
            content = match.group('content')

            attr = {}

            for match in re.finditer(cls.RE_OPTION, options):
                key = match.group('key')
                value = match.group('value')
                attr[key] = value

            try:
                attr['tags'] = cls.get_tag_list(attr['tags'])
            except KeyError:
                pass

            try:
                attr['modified'] = cls.string_to_date(attr['modified'])
            except KeyError:
                pass

            try:
                attr['created'] = cls.string_to_date(attr['created'])
            except KeyError:
                continue  # don't include tiddlers without creation tag

            try:
                if attr['title'].startswith('$:/'):
                    continue  # don't include tiddlers, whose title start with '$:/'
            except KeyError:
                continue  # don't include tiddlers without title

            yield cls(content, **attr)

    @classmethod
    def parse_from_string(cls, buffer):
        """A Tiddler factory
        If buffer contains a tiddler, a Tiddler instance of the first tiddler is returned.
        If buffer does not contain any tiddler, None is returned.

        """
        try:
            return next(cls.finditer(buffer))
        except StopIteration:
            return None

    def __str__(self):
        result = (self.title + '\n' +
                  '\ttags: ' + str(self.tags) + '\n' +
                  '\tcreated: ' + str(self.created) + ', '
                  '\tmodified: ' + str(self.modified) + '\n'
                  '\t' + reprlib.repr(self.content))

        return result

    def __repr__(self):
        attr = {key: value for key, value in self.__dict__.items()
                if not key.startswith('__') and key not in {'content'}}

        attr_string = ', '.join('{}={}'.format(key, reprlib.repr(value))
                                for key, value in attr.items())

        result = 'Tiddler({}, {})'.format(reprlib.repr(self.content), attr_string)

        return result

    def export_content(self, format='md', latex_gif=False):
        '''export the tiddler content.
        format is any valid pandoc format specifier.
        first, the tiddler content is converted to github flavored markdown.
        then pypandoc is used to convert the md file to the desired format.
        '''
        if self.type_ == 'text/vnd.tiddlywiki':
            content = type(self).convert_tw5_to_md(self.content, latex_gif=latex_gif)
        elif self.type_ == 'text/html':
            content = pypandoc.convert_text(self.content, 'md', format='html')
        elif self.type_ == 'text/x-markdown':
            content = self.content
            print(type(content))
        else:
            content = self.content

        return pypandoc.convert_text(content, format, format='md')

    def export(self, format='md', latex_gif=False):
        '''the tiddler is exported to a markdown string'''
        result = '# ' + self.title + '\n'
        result += '**created**: ' + str(self.created) + ',  '
        result += '**last modified**: ' + str(self.modified) + '\n\n'
        result += '**keywords**: ' + str(self.tags) + '\n\n---\n\n'
        result += self.export_content(latex_gif=latex_gif)

        try:
            result = pypandoc.convert_text(result, format, format='md')
        except: # TODO: specify error
            print("error occured")
            result = None

        return result

    def export_to_file(self, path, format=None):

        if format is None:
            format = path.split('.')[-1]
            # format = os.path.splitext(path)[1][1:]

        md = self.export()

        if format == 'pdf':
            # pandoc uses latex when converting to pdf.
            # unfortunately, the latex packet inputenc.sty doesn't use the utf-8 codec for unicode
            # (see: http://texdoc.net/texmf-dist/doc/latex/base/inputenc.pdf).
            # hence, some special characters can lead to runtime errors,
            # when pandocs tries to convert to latex.
            # to avoid these errors, the unicode string md is first encoded with a codec
            # (such as latin-1) that lacks these special characters and has less code points than utf-8.
            # (a list of codecs in python is https://docs.python.org/3.6/library/codecs.html#standard-encodings)
            # some code points corresponding to exotic characters
            # will be lost during this encoding (errors='ignore').
            # the (possibly trimmed) byte-string is then decoded back to unicode with the consequence
            # that all 'dangerous' characters are cut off.
            md = md.encode('latin-1', errors='ignore').decode('latin-1')

        pypandoc.convert_text(md, format, format='md', outputfile=path)

    # TODO: use export_to_file
    def open_in_browser(self, format='html', latex_gif=False):

        with tempfile.NamedTemporaryFile('w', suffix='.'+format, delete=False) as fh:
            md = self.export(format=format, latex_gif=latex_gif)
            fh.write(md)

        webbrowser.get(using='chrome').open('file://' + fh.name, new = 1)


if __name__ == "__main__":

    tiddler_string = r"""
<div created="20180108222550419" modified="20180111174922056" tags="[[multi word tag]] tag2 tag3" title="just a test" tmap.id="8b72e085-396b-4145-92aa-6793964cedad">
<pre>!This is a test tiddler.

* bullet
* points

# enumeration
# one
# two

''bold'' //italic//

in line math formula $$a^2+b^2=c^2$$. this is the [[pythagorean theorem|https://en.wikipedia.org/wiki/Pythagorean_theorem]].

latex equation:
$$
a^2+b^2=c^2.
$$</pre>
</div>"""

    tiddler = Tiddler.parse_from_string(tiddler_string)

    print(tiddler)

    tiddler.open_in_browser()
from dexy.filter import DexyFilter
import dexy.exceptions
import os

try:
    from docutils import core
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class RestructuredTextBase(DexyFilter):
    """
    Base class for ReST filters using the docutils library.
    """
    aliases = []

    _settings = {
            "input-extensions" : [".rst", ".txt"],
            'output-extensions' : [".html", ".tex", ".xml"],
            'output' : True,
            'writer' : ("Specify rst writer to use (not required: dexy will attempt to determine automatically from filename if not specified).", None),
            'stylesheet' : ("Stylesheet arg to pass to rst", None),
            'template' : ("Template arg to pass to rst", None),
            }

    @classmethod
    def is_active(klass):
        return AVAILABLE

    def docutils_writer_name(self):
        if self.setting('writer'):
            return self.setting('writer')
        elif self.ext == ".html":
            return 'html'
        elif self.ext == ".tex":
            return 'latex2e'
        elif self.ext == ".xml":
            return 'docutils_xml'
        else:
            raise Exception("unsupported extension %s" % self.ext)

class RestructuredText(RestructuredTextBase):
    """
    A 'native' ReST filter which uses the docutils library.

    Look for configuration options for writers here:
    http://docutils.sourceforge.net/docs/user/config.html
    """
    aliases = ['rst']
    skip_settings = 'settings-not-for-settings-overrides'
    _settings = {
            'allow-any-template-extension' : ("Whether to NOT raise an error if template extension does not match document extension.", False),
            skip_settings : (
                "Which of the settings should NOT be passed to settings_overrides.",
                ['writer']
                )
            }

    def process(self):
        def skip_setting(key):
            in_base_filter = key in DexyFilter._settings
            in_skip = key in self.setting(self.skip_settings) or key == self.skip_settings
            return in_base_filter or in_skip

        settings_overrides = dict((k.replace("-", "_"), v) for k, v in self.setting_values().iteritems() if v and not skip_setting(k))
        writer_name = self.docutils_writer_name()

        self.log_debug("settings for rst: %r" % settings_overrides)
        self.log_debug("rst writer: %s" % writer_name)

        # Check that template extension matches output.
        if 'template' in settings_overrides and not self.setting('allow-any-template-extension'):
            template = settings_overrides['template']
            template_ext = os.path.splitext(template)[1]
            if not template_ext == self.ext:
                msg = "You requested template '%s' with extension '%s' for %s, does not match document extension of '%s'"
                args = (template, template_ext, self.key, self.ext)
                raise dexy.exceptions.UserFeedback(msg % args)

        try:
            core.publish_file(
                    source_path = self.input_data.storage.data_file(),
                    destination_path = self.output_data.storage.data_file(),
                    writer_name=self.docutils_writer_name(),
                    settings_overrides=settings_overrides
                    )
        except ValueError as e:
            if "Invalid placeholder in string" in e.message and 'template' in settings_overrides:
                self.log_warn("you are using template '%s'. is this correct?" % settings_overrides['template'])
            raise e
        except Exception as e:
            self.log_warn("An error occurred while generating reStructuredText.")
            self.log_warn("source file %s" % (self.input_data.storage.data_file()))
            self.log_warn("settings for rst: %r" % settings_overrides)
            self.log_warn("rst writer: %s" % writer_name)
            raise e

class RstBody(RestructuredTextBase):
    """
    Returns just the body part of an ReST document.
    """
    aliases = ['rstbody']

    def process_text(self, input_text):
        parts = core.publish_parts(
                input_text,
                writer_name=self.docutils_writer_name(),
                )
        if parts.has_key('title') and parts['title']:
            self.update_all_args({'title' : parts['title']})

        return parts['body']

class RstDocParts(DexyFilter):
    """
    Returns key-value storage of document parts.
    """
    aliases = ['rstdocparts']
    _settings = {
            'input-extensions' : [".rst", ".txt"],
            'output-data-type' : 'keyvalue',
            'output-extensions' : ['.sqlite3', '.json'],
            'writer' : ("Specify rst writer to use.", 'html')
            }

    def process(self):
        input_text = unicode(self.input_data)

        parts = core.publish_parts(
                input_text,
                writer_name = self.setting('writer')
                )

        for k, v in parts.iteritems():
            self.output_data.append(k, v)
        self.output_data.save()
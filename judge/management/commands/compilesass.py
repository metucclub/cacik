import os
import sass

from django.conf import settings
from django.utils.encoding import force_bytes
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Compile SASS into CSS outside of the request/response cycle"
    filenames = ['content-description', 'ranks', 'table', 'style']

    def __init__(self):
        self.sass_output_style = getattr(settings, 'SASS_OUTPUT_STYLE',
                                         'nested' if settings.DEBUG else 'compressed')
        self.sass_precision = int(getattr(settings, 'SASS_PRECISION', 8))

        super(Command, self).__init__()

    def handle(self, *args, **options):
        for file in Command.filenames:
            self.compile_sass(file)

    def compile_sass(self, sass_filename):
        compile_kwargs = {
            'filename': os.path.join(settings.BASE_DIR, 'resources' , 'scss', sass_filename + '.scss'),
            'include_paths': [os.path.join(settings.BASE_DIR, 'resources', 'scss')],
        }

        if self.sass_precision:
            compile_kwargs['precision'] = self.sass_precision

        if self.sass_output_style:
            compile_kwargs['output_style'] = self.sass_output_style

        content = sass.compile(**compile_kwargs)

        self.save_to_destination(content, sass_filename)

        print('Compiled SASS/SCSS file: {0}\n'.format(sass_filename))


    def save_to_destination(self, content, sass_filename):
        destination = os.path.join(settings.STATIC_ROOT, 'css', sass_filename + '.css')

        with open(destination, 'wb') as fh:
            fh.write(force_bytes(content))
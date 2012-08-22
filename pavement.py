import sys
from paver.easy import *
from paver import doctools
from paver.setuputils import setup

PYCOMPILE_CACHES = ['*.pyc', '*$py.class']

options(
        sphinx=Bunch(builddir='.build'),
)


def sphinx_builddir(options):
    return path('docs') / options.sphinx.builddir / 'html'


@task
def clean_docs(options):
    sphinx_builddir(options).rmtree()


@task
@needs('clean_docs', 'paver.doctools.html')
def html(options):
    destdir = path('Documentation')
    destdir.rmtree()
    builtdocs = sphinx_builddir(options)
    builtdocs.move(destdir)


@task
@needs('paver.doctools.html')
def qhtml(options):
    destdir = path('Documentation')
    builtdocs = sphinx_builddir(options)
    sh('rsync -az {0}/ {1}'.format(builtdocs, destdir))


@task
@needs('clean_docs', 'paver.doctools.html')
def ghdocs(options):
    builtdocs = sphinx_builddir(options)
    sh("git checkout gh-pages && \
            cp -r {0}/* .    && \
            git commit . -m 'Rendered documentation for Github Pages.' && \
            git push origin gh-pages && \
            git checkout master".format(builtdocs))


@task
@needs('clean_docs', 'paver.doctools.html')
def upload_pypi_docs(options):
    builtdocs = path('docs') / options.builddir / 'html'
    sh("{0} setup.py upload_sphinx --upload-dir='{1}'".format(
        sys.executable, builtdocs))


@task
@needs('upload_pypi_docs', 'ghdocs')
def upload_docs(options):
    pass


@task
def autodoc(options):
    sh('extra/release/doc4allmods flower')


@task
def verifyindex(options):
    sh('extra/release/verify-reference-index.sh')


@task
def verifyconfigref(options):
    sh('PYTHONPATH=. {0} extra/release/verify_config_reference.py \
            docs/configuration.rst'.format(sys.executable))


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors'),
])
def flake8(options):
    noerror = getattr(options, 'noerror', False)
    complexity = getattr(options, 'complexity', 22)
    sh("""flake8 flower | perl -mstrict -mwarnings -nle'
        my $ignore = m/too complex \((\d+)\)/ && $1 le {0};
        if (! $ignore) {{ print STDERR; our $FOUND_FLAKE = 1 }}
    }}{{exit $FOUND_FLAKE;
        '""".format(complexity), ignore_error=noerror)


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors'),
])
def flakeplus(options):
    noerror = getattr(options, 'noerror', False)
    sh('flakeplus flower', ignore_error=noerror)


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors')
])
def flakes(options):
    flake8(options)
    flakeplus(options)


@task
def clean_readme(options):
    path('README').unlink()
    path('README.rst').unlink()


@task
@needs('clean_readme')
def readme(options):
    sh('{0} extra/release/sphinx-to-rst.py docs/templates/readme.txt \
            > README.rst'.format(sys.executable))


@task
def bump(options):
    sh("extra/release/bump_version.py flower/__init__.py")

@task
@cmdopts([
    ('coverage', 'c', 'Enable coverage'),
    ('verbose', 'V', 'Make more noise'),
])
def test(options):
    cmd = 'nosetests'
    if getattr(options, 'coverage', False):
        cmd += ' --with-coverage3'
    if getattr(options, 'verbose', False):
        cmd += ' --verbosity=2'
    sh(cmd)


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors'),
])
def pep8(options):
    noerror = getattr(options, 'noerror', False)
    return sh("""find . -name "*.py" | xargs pep8 | perl -nle'\
            print; $a=1 if $_}{exit($a)'""", ignore_error=noerror)


@task
def removepyc(options):
    sh('find . -type f -a \\( {0} \\) | xargs rm'.format(
        ' -o '.join("-name '{0}'".format(pat) for pat in PYCOMPILE_CACHES)))


@task
@needs('removepyc')
def gitclean(options):
    sh('git clean -xdn')


@task
@needs('removepyc')
def gitcleanforce(options):
    sh('git clean -xdf')


@task
@needs('flakes', 'autodoc', 'verifyindex',
       'verifyconfigref', 'test', 'gitclean')
def releaseok(options):
    pass


@task
@needs('releaseok', 'removepyc', 'upload_docs')
def release(options):
    pass


@task
def verify_authors(options):
    sh('git shortlog -se | cut -f2 | extra/release/attribution.py')

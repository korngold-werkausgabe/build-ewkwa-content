from pathlib import Path

# XML namespaces
NAMESPACES = {
    'mei': 'http://www.music-encoding.org/ns/mei',
    'xml': 'http://www.w3.org/XML/1998/namespace',
    'edirom': 'http://www.edirom.de/ns/1.3',
    'xlink': 'http://www.w3.org/1999/xlink'
}

base_path = Path(__file__).parent
base_path_test=Path('.')

LOCAL_PATHS = {
    'frbr': Path.joinpath(base_path_test, Path('frbr-tree.xml')),
    'edirom-config': Path.joinpath(base_path_test, Path('Edirom-Config')),
    '_edirom': Path.joinpath(base_path_test, Path('Edirom')),
    'conc': Path.joinpath(base_path_test, Path('Konkordanzen')),
    'criticalRemarks': Path.joinpath(base_path_test, Path('Textkritische-Anmerkungen')),
    'kbSources': Path.joinpath(base_path_test, Path('Quellenuebersicht')),
    'tmp': Path.joinpath(base_path_test, Path('tmp')),
    'scripts': Path(__file__).parent,
    'sources': Path.joinpath(base_path_test, Path('Quellen')),
    'templates': Path.joinpath(base_path_test, Path('build-ewkwa-content') / 'build-edirom' / 'templates')
}

SCRIPTS = {
    'prepare_sources': Path.joinpath(base_path / 'scripts' / 'prepareSources.xsl'),
    'build_nav': Path.joinpath(base_path / 'scripts' / 'buildNav.xsl'),
    'build_conc': Path.joinpath(base_path / 'scripts' / 'buildConnectionsByXML.xql'),
    'build_edirom_file': Path.joinpath(base_path / 'scripts' / 'buildEdiromFile.xsl')
}

TEMPLATES = {
    'template_edirom_file': Path.joinpath(base_path / 'templates' / 'template_edirom-file.xml')
}
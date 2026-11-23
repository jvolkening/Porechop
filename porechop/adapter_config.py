"""Read and write the external adapter sequence configuration."""

import json

from .adapters import ADAPTERS, BARCODE_CONTEXTS, Adapter


def write_defaults(path):
    adapters = []
    for adapter in ADAPTERS:
        entry = {'name': adapter.name}
        for key, sequence in [('start', adapter.start_sequence), ('end', adapter.end_sequence)]:
            if sequence:
                entry[key] = {'name': sequence[0], 'sequence': sequence[1]}
        adapters.append(entry)
    with open(path, 'x', encoding='utf-8') as output:
        json.dump({'version': 1, 'adapters': adapters, 'barcode_contexts': BARCODE_CONTEXTS},
                  output, indent=2)
        output.write('\n')


def load_adapters(path):
    with open(path, encoding='utf-8') as source:
        config = json.load(source)
    if not isinstance(config, dict) or set(config) != {'version', 'adapters', 'barcode_contexts'} or \
            config['version'] != 1 or not isinstance(config['adapters'], list):
        raise ValueError('expected version 1, adapters and barcode_contexts')
    if not config['adapters']:
        raise ValueError('adapters array must not be empty')

    adapters, names = [], set()
    for index, entry in enumerate(config['adapters'], 1):
        label = 'adapter {}'.format(index)
        if not isinstance(entry, dict) or set(entry) - {'name', 'start', 'end'}:
            raise ValueError('{} must contain only name, start and end'.format(label))
        name = _name(entry.get('name'), label)
        if name in names:
            raise ValueError('duplicate adapter name: {}'.format(name))
        names.add(name)
        start = _sequence(entry.get('start'), label + ' start')
        end = _sequence(entry.get('end'), label + ' end')
        if not start and not end:
            raise ValueError('{} must have a start or end sequence'.format(label))
        if name.startswith('Barcode '):
            if not start or not end:
                raise ValueError('{} barcode requires start and end sequences'.format(label))
            reverse = '(reverse)' in name.lower()
            forward = '(forward)' in name.lower()
            if forward == reverse or ('_rev' in start[0]) != reverse:
                raise ValueError('{} barcode orientation must agree with its start name'
                                 .format(label))
        adapters.append(Adapter(name, start_sequence=start, end_sequence=end))
    contexts = config['barcode_contexts']
    if not isinstance(contexts, dict) or set(contexts) != set(BARCODE_CONTEXTS):
        raise ValueError('barcode_contexts must contain all default context fields')
    for key, sequence in contexts.items():
        if not isinstance(sequence, str) or any(base not in 'ACGTN' for base in sequence.upper()):
            raise ValueError('barcode context {} must contain only A, C, G, T or N'.format(key))
        contexts[key] = sequence.upper()
    return adapters, contexts


def _name(value, label):
    if not isinstance(value, str) or not value.strip() or \
            any(c in value for c in '/\\\n\r\0'):
        raise ValueError('{} has an invalid name'.format(label))
    return value


def _sequence(value, label):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'name', 'sequence'}:
        raise ValueError('{} must contain name and sequence'.format(label))
    name = _name(value['name'], label)
    sequence = value['sequence']
    if not isinstance(sequence, str) or not sequence or \
            any(base not in 'ACGTN' for base in sequence.upper()):
        raise ValueError('{} sequence must contain only A, C, G, T or N'.format(label))
    return name, sequence.upper()

import requests
import json

BLAZEGRAPH_URL = 'http://localhost:9999/blazegraph/sparql'

MOCK_DATA = [
    {
        'nct_id': 'NCT00000001',
        'organization': 'Acme Corp',
        'primary_completion_date': '2023-01-01',
        'compliance': 'on time'
    },
    {
        'nct_id': 'NCT00000002',
        'organization': 'Beta Org',
        'primary_completion_date': '2024-06-01',
        'compliance': 'late'
    }
]

PREFIXES = """\
PREFIX ct: <http://example.org/ct/>
"""

def insert_mock_data():
    triples = []
    for trial in MOCK_DATA:
        triples.append(f"ct:{trial['nct_id']} ct:organization '{trial['organization']}' .")
        triples.append(f"ct:{trial['nct_id']} ct:primary_completion_date '{trial['primary_completion_date']}' .")
        triples.append(f"ct:{trial['nct_id']} ct:compliance '{trial['compliance']}' .")
    data = PREFIXES + "\n" + "\n".join(triples)
    requests.post(BLAZEGRAPH_URL, data={'update': f'INSERT DATA {{ {data} }}'})

if __name__ == '__main__':
    insert_mock_data()

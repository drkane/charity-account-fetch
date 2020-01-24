import os
import base64
import requests

for f in os.listdir("."):
    if not f.endswith('.pdf'):
        continue
    doc_id = f.replace(".pdf", '')
    print(doc_id)
    with open(f, "rb") as b:
        r = requests.put(
            'http://localhost:9200/charityaccounts/_doc/{}?pipeline=accounts'.format(doc_id),
            json={
                "filedata": base64.b64encode(b.read()).decode('utf8')
            }
        )
        print(r.json())

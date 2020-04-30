var charCache = {};

function getRecordData(record) {
    if (!record[0].match('[1-9][0-9]{5,6}')) {
        return null;
    }
    var fye;
    if (record.length > 1 && record[1].match('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}')) {
        fye = record[1];
    }

    if (record[0] in charCache) {
        return new Promise((_) => charCache[record[0]]);
    }

    return fetch(`/charity/${record[0]}.json`)
        .then((r) => r.json())
        .then((data) => {
            charCache[record[0]] = data;
            data['fye'] = fye;
            return data;
        })
        .catch(function (error) {
            console.log(error);
            return {
                fye: fye,
                data: {
                    regno: record[0],
                },
                error: 'Charity not found',
            };
        });
}

function createRecordCell(f, v, classList) {
    var td = document.createElement('td');
    td.classList.add(f, 'pa2');
    if (classList) {
        classList.forEach((c) => {
            td.classList.add(c);
        });
    }
    if (v instanceof HTMLElement) {
        td.append(v);
    } else if (v) {
        td.innerText = v;
    }
    return td;
}

function parseRecordData(record) {
    data = {
        regno: record['data']['regno'],
        status: 'unknown',
        name: null,
        error: record.error,
        fyend: null,
        income: null,
        spending: null,
        doc_url: null,
        url: null,
        fetch: false,
    };
    if(record.error){
        data['status'] = 'error';
        return data
    }

    data['name'] = record['data']['charity']['names'][0]['value'];
    
    if (record['fye']) {
        fy = record['data']['charity']['finances'].find((f) => f['fyend'] == record['fye']);
        if (!fy) {
            data['status'] = 'FYE not found';
        } else {
            data['status'] = 'Matched';
            data['income'] = fy['income'];
            data['spending'] = fy['spending'];
            data['fyend'] = fy['fyend'];
            data['doc_url'] = fy['doc_url'];
            data['url'] = fy['url'];
        }
    } else {
        fy = record['data']['charity']['finances'].find((f) => ('url' in f));
        if (!fy) {
            fy = record['data']['charity']['finances'][0];
            data['status'] = 'No account PDFs available';
        } else {
            data['status'] = 'Latest with url';
        }
        data['income'] = fy['income'];
        data['spending'] = fy['spending'];
        data['fyend'] = fy['fyend'];
        data['doc_url'] = fy['doc_url'];
        data['url'] = fy['url'];
    }
    if(data['doc_url']){
        data['status'] = 'Document already fetched';
    } else if(data['url']){
        data['fetch'] = true;
    }
    return data
}

function createRecordRow(record){

    var nf = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 0 });
    var tr = document.createElement('tr');
    for (let [key, value] of Object.entries(record)) {
        tr.dataset[key] = value;
    }    
    tr.id = `record-${record.regno}`;
    tr.classList.add('record-row');

    if (record.error) {
        tr.classList.add('bg-washed-red');
        tr.append(createRecordCell('regno', record.regno));
        message = createRecordCell('status', record.error);
        message.setAttribute('colspan', 5);
        tr.append(message);
        return tr;
    }

    tr.append(createRecordCell('regno', record.regno));
    tr.append(createRecordCell('name', record.name));
    if (record.fyend) {
        tr.append(createRecordCell('fye', record.fyend));
        if (typeof data['income'] !== 'undefined') {
            tr.append(createRecordCell('income', nf.format(data['income']), ['tr']));
            tr.append(createRecordCell('spending', nf.format(data['spending']), ['tr']));
        } else {
            tr.append(createRecordCell('income', null, ['tr']));
            tr.append(createRecordCell('spending', null, ['tr']));
        }
        if (data["doc_url"]) {
            let a = document.createElement('a');
            a.href = data['doc_url'];
            a.innerText = 'Document exists';
            tr.classList.add('bg-light-green');
            tr.append(createRecordCell('status', a));
        } else if (data['url']) {
            let a = document.createElement('a');
            a.href = data['url'];
            a.innerText = `Fetch url [${data['status']}]`;
            tr.append(createRecordCell('status', a));
        } else {
            tr.classList.add('bg-washed-red');
            tr.append(createRecordCell('status', data['status']));
        }
    } else {
        tr.append(createRecordCell('fye', null));
        tr.append(createRecordCell('income', null));
        tr.append(createRecordCell('spending', null));
        tr.append(createRecordCell('status', data['status']));
    }
    return tr;
}

document.addEventListener("DOMContentLoaded", function () {

    Array.from(document.getElementsByClassName('data-input')).forEach((el) => {
        el.value = '';
        el.addEventListener('change', (e) => {
            e.preventDefault();
            var file;
            var source;
            if (e.target.files) {
                file = e.target.files[0];
                source = file.name;
            } else if (e.target.value) {
                file = e.target.value;
                source = 'Text box';
            }
            if (file) {
                Papa.parse(file, {
                    preview: 100,
                    complete: (results) => {
                        document.getElementById('file-source').innerText = source;
                        var table = document.getElementById('preview-data');
                        table.innerHtml = '';
                        if (results['data']) {
                            var rowCount = 0;
                            results['data'].forEach((row) => {
                                row = getRecordData(row);
                                if (row) {
                                    row.then((data) => {
                                        rowCount++;
                                        data = parseRecordData(data);
                                        var tr = createRecordRow(data);
                                        table.append(tr);
                                        document.getElementById('file-values').innerText = `(${rowCount} records found)`;
                                    })
                                }
                            });
                        }
                    }
                });
            }
        });
    });

    document.getElementById('upload-docs').addEventListener('click', (e) => {
        e.preventDefault();
        Array.from(document.getElementsByClassName('record-row')).forEach((row) => {
            const id = row.id.replace('record-', '');
            if(row.dataset.fetch=="true"){
                const formData = new FormData();
                formData.append('url', row.dataset.url);
                fetch('/doc/upload.json', {
                    method: 'POST',
                    body: formData
                })
                .then(res => res.json())
                .then(res => {
                    console.log(res);
                })
            }
        });
    });
});
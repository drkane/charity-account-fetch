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

function createRecordRow(record) {
    var nf = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 0 });
    var tr = document.createElement('tr');
    tr.id = `record-${record['data']['regno']}`;
    tr.classList.add('record-row');
    var fy = {};
    if (record['fye']) {
        fy = record['data']['charity']['finances'].find((f) => f['fyend'] == record['fye']);
        if (!fy) {
            fy = {
                'status': 'FYE not found'
            }
        } else {
            fy['status'] = 'Matched';
        }
    } else {
        fy = record['data']['charity']['finances'].find((f) => ('url' in f));
        if (!fy) {
            fy = record['data']['charity']['finances'][0];
            fy['status'] = 'No account PDFs available';
        } else {
            fy['status'] = 'Latest with url';
        }
    }

    tr.dataset.regno = record['data']['regno'];

    tr.append(createRecordCell('regno', record['data']['regno']));
    tr.append(createRecordCell('name', record['data']['charity']['names'][0]['value']));
    if (fy['fyend']) {
        tr.append(createRecordCell('fye', fy['fyend']));
        tr.dataset.fyend = fy['fyend'];
        if (typeof fy['income'] !== 'undefined') {
            tr.append(createRecordCell('income', nf.format(fy['income']), ['tr']));
            tr.append(createRecordCell('spending', nf.format(fy['spending']), ['tr']));
        } else {
            tr.append(createRecordCell('income', null, ['tr']));
            tr.append(createRecordCell('spending', null, ['tr']));
        }
        if (fy["doc_url"]) {
            let a = document.createElement('a');
            a.href = fy['doc_url'];
            a.innerText = 'Document exists';
            tr.classList.add('bg-light-green');
            tr.append(createRecordCell('status', a));
        } else if (fy['url']) {
            let a = document.createElement('a');
            a.href = fy['url'];
            a.innerText = `Fetch url [${fy['status']}]`;
            tr.dataset.url = fy['url'];
            tr.append(createRecordCell('status', a));
        } else {
            tr.classList.add('bg-washed-red');
            tr.append(createRecordCell('status', fy['status']));
        }
    } else {
        tr.append(createRecordCell('fye', null));
        tr.append(createRecordCell('income', null));
        tr.append(createRecordCell('spending', null));
        tr.append(createRecordCell('status', fy['status']));
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
                                        var tr = createRecordRow(data);
                                        table.append(tr);
                                        document.getElementById('file-values').innerText = `(${rowCount} values found)`;
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
            console.log(row.dataset);
        });
    });
});
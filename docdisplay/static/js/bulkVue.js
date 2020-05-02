var data = {
    charCache: {},
    records: [],
    textAreaRecords: '',
    source: '',
}

var charityRecord = {
    template: `
    <tr v-bind:class="{ 'bg-washed-red': error }">
    <template v-if="error">
            <td class="pa2">{{ regno }}</td>
            <td class="pa2">{{ fye }}</td>
            <td class="pa2" colspan="4">
                <strong class="red">ERROR:</strong> {{ error }}
            </td>
    </template>
    <template v-else>
            <td class="pa2">{{ regno }}</td>
            <td class="pa2">{{ fye }}</td>
            <td class="pa2">{{ name }}</td>
            <td class="pa2 tr">{{ numberFormat(income) }}</td>
            <td class="pa2 tr">{{ numberFormat(spending) }}</td>
            <td class="pa2">{{ status }}</td>
        </template>
    </tr>`,
    props: ['regno', 'fye'],
    data: function(){
        return {
            income: null,
            spending: null,
            status: 'fetching',
            name: null,
            doc_url: null,
            url: null,
            error: null,
        }
    },
    mounted: function(){
        var this_ = this;
        getRecordData(
            this.regno,
            this.fye,
            data.charCache
        ).then((record) => {
            console.log(record);
            record = parseRecordData(record);
            this_.income = record.income;
            this_.spending = record.spending;
            this_.status = record.status;
            this_.name = record.name;
            this_.doc_url = record.doc_url;
            this_.url = record.url;
            this_.error = record.error;
        });
    },
    methods: {
        fetchDocument: (event) => {

        },
        numberFormat: function(n){
            if(!n){return null};
            var nf = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 0 });
            return nf.format(n);
        }
    }
}

var vm = new Vue({
    el: "#bulk-upload",
    data: data,
    methods: {
        fetchFromTextArea: (event) => {
            fetchFromFile(vm.textAreaRecords);
            vm.source = 'Text area';
        }
    },
    components: {
        'charity-record': charityRecord
    }
});

function fetchFromFile(file){
    Papa.parse(file, {
        preview: 100,
        complete: (results) => {
            if (results['data']) {
                results['data'].forEach((record) => {
                    if (!record) { return };
                    if (!record[0].match('[1-9][0-9]{5,6}')) {
                        return;
                    }
                    var fye;
                    if (record.length > 1 && record[1].match('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}')) {
                        fye = record[1];
                    }
                    data.records.push({
                        regno: record[0],
                        fye: fye,
                    });
                });
            }
        }
    });
}

function getRecordData(regno, fye, charCache) {
    if (regno in charCache) {
        console.log(charCache[regno]);
        return new Promise((_) => charCache[regno]);
    }

    return fetch(`/charity/${regno}.json`)
        .then((r) => r.json())
        .then((record) => {
            charCache[regno] = record;
            record['fye'] = fye;
            return record;
        })
        .catch(function (error) {
            console.log(error);
            return {
                fye: fye,
                data: {
                    regno: regno,
                },
                error: 'Charity not found',
            };
        })
}

function parseRecordData(record) {
    row = {
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
        row['status'] = 'error';
        return row
    }

    row['name'] = record['data']['charity']['names'][0]['value'];
    
    if (record['fye']) {
        fy = record['data']['charity']['finances'].find((f) => f['fyend'] == record['fye']);
        if (!fy) {
            row['status'] = 'FYE not found';
        } else {
            row['status'] = 'Matched';
            row['income'] = fy['income'];
            row['spending'] = fy['spending'];
            row['fyend'] = fy['fyend'];
            row['doc_url'] = fy['doc_url'];
            row['url'] = fy['url'];
        }
    } else {
        fy = record['data']['charity']['finances'].find((f) => ('url' in f));
        if (!fy) {
            fy = record['data']['charity']['finances'][0];
            row['status'] = 'No account PDFs available';
        } else {
            row['status'] = 'Latest with url';
        }
        row['income'] = fy['income'];
        row['spending'] = fy['spending'];
        row['fyend'] = fy['fyend'];
        row['doc_url'] = fy['doc_url'];
        row['url'] = fy['url'];
    }
    if (row['doc_url']){
        row['status'] = 'Document already fetched';
    } else if (row['url']){
        row['fetch'] = true;
    }
    return row
}

// function createRecordRow(record){

//     var nf = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 0 });
//     var tr = document.createElement('tr');
//     for (let [key, value] of Object.entries(record)) {
//         tr.dataset[key] = value;
//     }    
//     tr.id = `record-${record.regno}`;
//     tr.classList.add('record-row');

//     if (record.error) {
//         tr.classList.add('bg-washed-red');
//         tr.append(createRecordCell('regno', record.regno));
//         message = createRecordCell('status', record.error);
//         message.setAttribute('colspan', 5);
//         tr.append(message);
//         return tr;
//     }

//     tr.append(createRecordCell('regno', record.regno));
//     tr.append(createRecordCell('name', record.name));
//     if (record.fyend) {
//         tr.append(createRecordCell('fye', record.fyend));
//         if (typeof data['income'] !== 'undefined') {
//             tr.append(createRecordCell('income', nf.format(data['income']), ['tr']));
//             tr.append(createRecordCell('spending', nf.format(data['spending']), ['tr']));
//         } else {
//             tr.append(createRecordCell('income', null, ['tr']));
//             tr.append(createRecordCell('spending', null, ['tr']));
//         }
//         if (data["doc_url"]) {
//             let a = document.createElement('a');
//             a.href = data['doc_url'];
//             a.innerText = 'Document exists';
//             tr.classList.add('bg-light-green');
//             tr.append(createRecordCell('status', a));
//         } else if (data['url']) {
//             let a = document.createElement('a');
//             a.href = data['url'];
//             a.innerText = `Fetch url [${data['status']}]`;
//             tr.append(createRecordCell('status', a));
//         } else {
//             tr.classList.add('bg-washed-red');
//             tr.append(createRecordCell('status', data['status']));
//         }
//     } else {
//         tr.append(createRecordCell('fye', null));
//         tr.append(createRecordCell('income', null));
//         tr.append(createRecordCell('spending', null));
//         tr.append(createRecordCell('status', data['status']));
//     }
//     return tr;
// }

// document.addEventListener("DOMContentLoaded", function () {

//     Array.from(document.getElementsByClassName('data-input')).forEach((el) => {
//         el.value = '';
//         el.addEventListener('change', (e) => {
//             e.preventDefault();
//             var file;
//             var source;
//             if (e.target.files) {
//                 file = e.target.files[0];
//                 source = file.name;
//             } else if (e.target.value) {
//                 file = e.target.value;
//                 source = 'Text box';
//             }
//             if (file) {
//                 Papa.parse(file, {
//                     preview: 100,
//                     complete: (results) => {
//                         document.getElementById('file-source').innerText = source;
//                         var table = document.getElementById('preview-data');
//                         table.innerHtml = '';
//                         if (results['data']) {
//                             var rowCount = 0;
//                             results['data'].forEach((row) => {
//                                 row = getRecordData(row);
//                                 if (row) {
//                                     row.then((data) => {
//                                         rowCount++;
//                                         data = parseRecordData(data);
//                                         var tr = createRecordRow(data);
//                                         table.append(tr);
//                                         document.getElementById('file-values').innerText = `(${rowCount} records found)`;
//                                     })
//                                 }
//                             });
//                         }
//                     }
//                 });
//             }
//         });
//     });

//     document.getElementById('upload-docs').addEventListener('click', (e) => {
//         e.preventDefault();
//         Array.from(document.getElementsByClassName('record-row')).forEach((row) => {
//             const id = row.id.replace('record-', '');
//             if(row.dataset.fetch=="true"){
//                 const formData = new FormData();
//                 formData.append('url', row.dataset.url);
//                 fetch('/doc/upload.json', {
//                     method: 'POST',
//                     body: formData
//                 })
//                 .then(res => res.json())
//                 .then(res => {
//                     console.log(res);
//                 })
//             }
//         });
//     });
// });
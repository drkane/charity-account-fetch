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
            <td class="pa2">{{ fyend }}</td>
            <td class="pa2" colspan="4">
                <strong class="red">ERROR:</strong> {{ error }}
            </td>
    </template>
    <template v-else>
            <td class="pa2">{{ regno }}</td>
            <td class="pa2">{{ fyend }}</td>
            <td class="pa2">{{ name }}</td>
            <td class="pa2 tr">{{ numberFormat(income) }}</td>
            <td class="pa2 tr">{{ numberFormat(spending) }}</td>
            <td class="pa2">{{ status }}</td>
        </template>
    </tr>`,
    props: ['regno', 'initialFyend'],
    data: function(){
        return {
            income: null,
            spending: null,
            name: null,
            doc_url: null,
            url: null,
            fyend: this.initialFyend,
            error: null,
            fye_source: null,
            loading: false,
        }
    },
    mounted: function(){
        // setup event for fetching document
        this.$parent.$on('fetch-documents', this.fetchDocument);

        // get the record data
        this.fetchCharity();
    },
    computed: {
        status: function(){
            if(this.loading){
                return 'Loading';
            }
            if(this.error){
                return 'Error';
            }
            if(this.doc_url){
                return 'Document fetched';
            }
            if(!this.url){
                return 'No document available';
            }
            if(this.fye_source){
                return this.fye_source;
            }
            return 'To fetch';
        }
    },
    methods: {

        // fetch details about the charity
        fetchCharity: function () {
            var this_ = this;
            this.loading = true;
            getRecordData(
                this.regno,
                this.fyend,
                data.charCache
            ).then((record) => {
                record = parseRecordData(record, this_.fyend);
                this_.income = record.income;
                this_.spending = record.spending;
                this_.fyend = record.fyend;
                this_.fye_source = record.fye_source;
                this_.name = record.name;
                this_.doc_url = record.doc_url;
                this_.url = record.url;
                this_.error = record.error;
                this_.loading = false;
            });
        },

        // start the process of uploading the document
        fetchDocument: function() {
            if(this.url && !this.doc_url){
                const formData = new FormData();
                var this_ = this;
                this.loading = true;
                formData.append('url', this.url);
                fetch('/doc/upload.json', {
                    method: 'POST',
                    body: formData
                })
                .then(res => res.json())
                .then(res => {
                    this_.doc_url = `/doc/${res.data.id}`;
                    this_.status = 'Document already fetched';
                    this_.loading = false;
                });
            } else if (!this.url) {
                this_.status = 'Document already fetched';
            }
        },

        // format a number
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
        },
        fetchDocuments: function(event){
            this.$emit('fetch-documents');
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
                    var fyend;
                    if (record.length > 1 && record[1].match('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}')) {
                        fyend = record[1];
                    }
                    if(data.records.find((item) => (
                        item.regno == record[0] & item.fyend == fyend
                    ))){return;}
                    data.records.push({
                        regno: record[0],
                        fyend: fyend,
                    });
                });
            }
        }
    });
}

function getRecordData(regno, fyend, charCache) {
    if (regno in charCache) {
        return new Promise((resolve) => resolve(charCache[regno]));
    }

    return fetch(`/charity/${regno}.json`)
        .then((r) => r.json())
        .then((record) => {
            charCache[regno] = record;
            record['fyend'] = fyend;
            return record;
        })
        .catch(function (error) {
            return {
                fyend: fyend,
                data: {
                    regno: regno,
                },
                error: 'Charity not found',
            };
        })
}

function parseRecordData(record, fyend) {
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
    
    if (fyend) {
        fy = record['data']['charity']['finances'].find((f) => f['fyend'] == fyend);
        if (!fy) {
            row['fye_source'] = 'FYE not found';
        } else {
            row['fye_source'] = 'Matched';
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
            row['fye_source'] = 'No account PDFs available';
        } else {
            row['fye_source'] = 'Latest with url';
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

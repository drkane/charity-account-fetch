'use strict';

class BulkUpload extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            stage: 0,
            records: [],
            recordSource: null,
            charCache: {},
            recordsToFetch: [],
        };
        this.setRecords = this.setRecords.bind(this);
    }

    setRecords = (file, source) => {
        Papa.parse(file, {
            preview: 100,
            complete: (results) => {
                if(results.data){
                    var records = results.data
                        .filter(r => r.length==2)
                        .map((r) => ({
                            regno: r[0],
                            fyend: r[1],
                        }));
                    this.setState((prevState) => ({
                        records: [...prevState.records, ...records],
                        recordSource: source,
                        stage: 1,
                    }));
                }
            }
        });
    }

    render() {
        var uploaders = <React.Fragment>
            <div className="w-100 w-50-l">
                <FileUpload setRecords={this.setRecords} />
            </div>
            <div className="w-100 w-50-l">
                <TextareaUpload setRecords={this.setRecords} />
            </div>
        </React.Fragment>

        if (this.state.records.length > 0) {
            return <React.Fragment>
                {uploaders}
                <p className="w-100">
                    <span className="b">File source: {this.state.recordSource}</span>
                </p>
                <p className="w-100">
                    <span>{this.state.records.length} records loaded</span>
                </p>

                <table id='' className="table collapse w-100 f6">
                    <thead>
                        <tr>
                            <th className="pa2 bb b--light-gray bw1 tl">Charity number</th>
                            <th className="pa2 bb b--light-gray bw1 tl">Charity name</th>
                            <th className="pa2 bb b--light-gray bw1 tl">Financial year end</th>
                            <th className="pa2 bb b--light-gray bw1 tr">Income</th>
                            <th className="pa2 bb b--light-gray bw1 tr">Spending</th>
                            <th className="pa2 bb b--light-gray bw1 tl">Status</th>
                        </tr>
                    </thead>
                    <tbody id='preview-data'>
                        {this.state.records.map((r, k) => <TableRow record={r} key={k} />)}
                    </tbody>
                </table>
            </React.Fragment>;
        }

        return uploaders;
    }
}

class FileUpload extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            file: null,
        };
        this.handleClick = this.handleClick.bind(this);
    }

    handleClick = function(e) {
        e.preventDefault();
        this.setState({
            file: e.target.files[0],
        })
        this.props.setRecords(e.target.files[0], 'csvfile');
    }

    render() {
        return <React.Fragment>
            <label className="db w-100 mt4 b">Upload a CSV file: </label>
            <input className="mt4 db cf data-input" type='file' name='file' id='file' onChange={this.handleClick} />
        </React.Fragment>
    }
}

class TextareaUpload extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            file: '',
        };
        this.handleClick = this.handleClick.bind(this);
        this.handleTextAreaChange = this.handleTextAreaChange.bind(this);
    }

    handleTextAreaChange = function (e) {
        e.preventDefault();
        this.setState({
            file: e.target.value,
        })
    }

    handleClick = function (e) {
        e.preventDefault();
        this.props.setRecords(this.state.file, 'textarea');
    }

    render() {
        console.log(this.state.file);
        return <React.Fragment>
            <label className="db w-100 mt4 b">Or paste a list of charities: </label>
            <textarea onChange={this.handleTextAreaChange} 
                      value={this.state.file} 
                      className="f6 f5-l input-reset ba bw1 b--black-20 db cf near-black bg-white pa2 lh-solid w5 br2-ns w-100 data-input" 
                      rows="8" 
                      id='list' 
                      placeholder='123456,2020-03-31' />
            <input onClick={this.handleClick} className="mt4 f5 f4-l button-reset fl pa3 no-underline tc bn bg-animate bg-yellow dim near-black pointer br2-ns" type='submit' id='upload-docs' value='Load records' />
        </React.Fragment>
    }
}

class TableRow extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            regno: this.props.record.regno,
            fyend: this.props.record.fyend,
            status: 'loading',
        };
    }

    componentDidMount() {
        fetch(`/charity/${this.state.regno}.json`)
            .then((r) => r.json())
            .then((record) => {
                console.log(record);
                var fy = {};
                if (this.state.fyend) {
                    fy = record['data']['charity']['finances'].find((f) => f['fyend'] == this.state.fyend);
                    if (!fy) {
                        this.setState({
                            status: 'error',
                            error: 'FYE not found'
                        });
                        return;
                    } else {
                        fy['status'] = 'fyend_available';
                    }
                } else {
                    fy = record['data']['charity']['finances'].find((f) => ('url' in f));
                    if (!fy) {
                        fy = record['data']['charity']['finances'][0];
                        fy['status'] = 'no_accounts_available';
                    } else {
                        fy['status'] = 'latest_fyend';
                    }
                }

                this.setState({
                    name: record.data.charity.names[0].value,
                    fyend: fy.fyend,
                    income: fy.income,
                    spending: fy.spending,
                    url: fy.url,
                    doc_url: fy.doc_url,
                    status: fy.status,
                })
            })
            .catch((error) => {
                console.log(error);
                this.setState({
                    status: 'error',
                    error: 'Could not find charity'
                })
            });
    }

    render() {
        if(this.state.status=='error' || this.state.error){
            return <tr className="bg-washed-red">
                <td className="pa2">{this.state.regno}</td>
                <td className="pa2" colSpan="4">{this.state.error}</td>
                <td className="pa2">Error</td>
            </tr>
        }

        var status = "";
        var trClass = "";
        if (this.state.doc_url){
            trClass = 'bg-washed-green';
            status = <a href={this.state.doc_url} target="_blank">Accounts available</a>;
        } else if (this.state.status == 'fyend_available'){
            trClass = 'bg-washed-yellow';
            status = 'Ready to fetch';
        } else if (this.state.status == 'no_accounts_available') {
            trClass = 'bg-washed-red';
            status = 'No accounts available';
        } else if (this.state.status == 'latest_fyend') {
            trClass = 'bg-washed-yellow';
            status = 'Ready to fetch (latest accounts)';
        }

        var nf = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', minimumFractionDigits: 0 });
        return <tr className={trClass}>
            <td className="pa2">{this.state.regno}</td>
            <td className="pa2">{this.state.name}</td>
            <td className="pa2">{this.state.fyend}</td>
            <td className="pa2 tr">{this.state.income && nf.format(this.state.income)}</td>
            <td className="pa2 tr">{this.state.income && nf.format(this.state.spending)}</td>
            <td className="pa2">{status}</td>
        </tr>
    }
}

const domContainer = document.querySelector('#bulk-upload');
ReactDOM.render(<BulkUpload />, domContainer);
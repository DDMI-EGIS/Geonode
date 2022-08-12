
// ==================================================================================================================
// ================================================PANEL TOGGLERS =================================================
// ==================================================================================================================

function openLegendPanel(){
    document.getElementById("right-panel").style.width = "16.67%"
    document.getElementById("right-panel").style.opacity = "100"

    for (let i = 0; i <= 500; i = i + 10) {
        if (i > 0) {
            setTimeout(mapResize, i)
        }
    }
}

function togglePanel(side){
    if(side == "left"){
        if (document.getElementById("left-panel").style.width == "0px"){
            document.getElementById("left-panel").style.width = "33.33%"
            document.getElementById("left-panel").style.opacity = "100"
        }
        else {
            document.getElementById("left-panel").style.width = "0px"
            document.getElementById("left-panel").style.opacity = "0"
        }; 
    }
    else if (side == "right") {
        if (document.getElementById("right-panel").style.width == "0px") {
            document.getElementById("right-panel").style.width = "16.67%"
            document.getElementById("right-panel").style.opacity = "100"
        }
        else {
            document.getElementById("right-panel").style.width = "0px"
            document.getElementById("right-panel").style.opacity = "0"
        }; 
    }

    for (let i = 0; i <= 500; i=i+10) {
        if(i>0){
            setTimeout(mapResize, i)
        }
    }
}

function mapResize(){
    getMap().invalidateSize()
}

// ==================================================================================================================
// ================================================ REACT COMPONENTS ================================================
// ==================================================================================================================

// LEGEND ACCORDION
class Accordion extends React.Component {
    static UIkitComponent;

    componentDidMount() {
        this.UIkitComponent = UIkit.accordion($(this.gridElement), {
            targets: this.props.targets,
            active: this.props.active,
            collapsible: this.props.collapsible,
            multiple: this.props.multiple,
            animation: this.props.animation,
            transition: this.props.transition,
            duration: this.props.duration
        });
    }

    componentDidUpdate() {
        this.UIkitComponent.$emit(event = 'update');
    }


    componentWillUnmount() {
        this.UIkitComponent.$destroy();

    }

    render() {
        return (
            <ul
                id={this.props.id}
                className={this.props.className}
                ref={(element) => { this.gridElement = element; }}
                data-uk-sortable="handle: .uk-sortable-handle">
                {this.props.children}
            </ul>
        );
    }
}

// LEGEND
class Legend extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            key:0,
            layers: []
        };
        this.addLegendItem = this.addLegendItem.bind(this);
    }

    componentDidMount() {
        // Attach listener to modify layer order on layer change
        UIkit.util.on('#legend_main_container', 'moved', function (item) {
            mainLayerManager.reloadMapLayers()
        });
    }

    addLegendItem(geonodeLayerId){
        var tempLayers = this.state.layers;
        var item = {
            key: this.state.key,
            id: geonodeLayerId,
        }
        
        tempLayers.push(item)

        var newKey = this.state.key + 1

        this.setState({
            layers: tempLayers,
            key: newKey,
        })

        return true;
    }

    render() {
        // the loop. it'll return array of react node.
        var legendItems = []
        if (this.state.layers !== []){
            for (const layer of this.state.layers) {
                legendItems.push(<LegendItem key={layer.key} layerid={layer.key} id={layer.id}></LegendItem>)
                legendItems = legendItems.reverse()
            }
        }
        return(
            <Accordion id={this.props.id} multiple="true" className="uk-padding-small uk-accordion">
                {legendItems}
            </Accordion>
        )
    }
}

// LEGEND ITEMS
class LegendItem extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            error: null,
            status: 'loading',
            hidden: false,
        };
        this.style = {
            opacity: 100,
            opacityOld: 100,
        };
        // Adding "this" var to custom functions
        this.handleZoomExtentClick = this.handleZoomExtentClick.bind(this);
        this.handleHideClick = this.handleHideClick.bind(this);
        this.handleOpacityChange = this.handleOpacityChange.bind(this);
        this.handleDelete = this.handleDelete.bind(this);
    }


    handleZoomExtentClick() {
        var polygon = this.state.bbox
        getMap().fitBounds(polygon.getBounds());
    }

    handleHideClick() {
        mainLayerManager.toggleMapLayerVisibility(this.props.layerid)
        if (this.state.hidden) {
            this.setState({
                status: 'ready',
                hidden: false,
            })
        }
        else {
            this.setState({
                status: 'ready',
                hidden: true,
            })
        }
    }

    handleOpacityChange(event) {
        if (!this.state.hidden) {
            mainLayerManager.setLayerOpacity(this.props.layerid, event.target.value)
        }
    }

    handleDelete() {
        mainLayerManager.removeMapLayer(this.props.layerid)
        this.setState({
            status: 'deleted',
        });
    }

    componentDidMount() {
        fetch( DOMAIN_NAME_FULL + "api/spade/resource_detail/" + this.props.id + "/")
            .then(res => res.json())
            .then(
                (result) => {
                    // Getting Layer coordinates from WMS servcie
                    fetch(DOMAIN_NAME_FULL+"capabilities/layer/" + this.props.id + "/")
                        .then(xml_text => xml_text.text())
                        .then(
                            (xml_text) => {

                                var parser = new DOMParser();
                                var xmlDoc = parser.parseFromString(xml_text, "text/xml");
                                var coordsXML = xmlDoc.getElementsByTagName("EX_GeographicBoundingBox")[0].children
                                var bbox_coords_correct = [
                                    [parseFloat(coordsXML[2].innerHTML), parseFloat(coordsXML[0].innerHTML)],
                                    [parseFloat(coordsXML[2].innerHTML), parseFloat(coordsXML[1].innerHTML)],
                                    [parseFloat(coordsXML[3].innerHTML), parseFloat(coordsXML[1].innerHTML)],
                                    [parseFloat(coordsXML[3].innerHTML), parseFloat(coordsXML[0].innerHTML)],
                                    [parseFloat(coordsXML[2].innerHTML), parseFloat(coordsXML[0].innerHTML)],
                                ]

                                // Setting the layer polygon extent
                                var bbox_polygon = L.polygon(bbox_coords_correct)
                                bbox_polygon.setStyle({
                                    color: "red",
                                    opacity: 0.5,
                                    fillColor: "red",
                                    fillOpacity: 0.3
                                });

                                // Setting the layer center marker
                                var icon = L.icon({
                                    iconUrl: '/static/gdc/img/layer_position_icon.png',
                                    iconSize: [30, 30],
                                    iconAnchor: [15, 15],
                                });
                                var bbox_center = L.marker(bbox_polygon.getBounds().getCenter(), { icon: icon })

                                // Setting title nicer
                                result.title = toTitleCase(result.title.replaceAll('_', ' '))

                                // Setting date nicer
                                var options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
                                var date_refactor = new Date(result.date)
                                result.date = date_refactor.toLocaleDateString("en-US", options)

                                // Getting thumbnail depending on custom thumbnail availability
                                if (result.curatedthumbnail != null) {
                                    var thumbnail_url = DOMAIN_NAME_FULL + result.curatedthumbnail.thumbnail_url.toString()
                                }
                                else {
                                    var thumbnail_url = result.thumbnail_url
                                }

                                // Getting proper legend URL
                                result.detail_url = DOMAIN_NAME_FULL + result.detail_url.toString()

                                // Loading layer
                                mainLayerManager.addMapLayer(result.alternate, this.props.layerid)

                                // Zoom to layer
                                getMap().fitBounds(bbox_polygon.getBounds());

                                // Changing state of react component
                                this.setState({
                                    status: 'ready',
                                    layerData: result,
                                    bbox: bbox_polygon,
                                    bbox_center: bbox_center,
                                    thumbnail_url: thumbnail_url
                                })
                            }
                        )
                },
                (error) => {
                    UIkit.notification('Error retrieving datasets results from server', 'danger');
                    this.setState({
                        status: 'error',
                        error
                    });
                }
            )
    }

    render() {

        if (this.state.hidden) {
            var classicon = "uk-text-danger"
        }
        else {
            var classicon = "uk-text-default"
        }

        if (this.state.status == 'ready') {

            var catList = []
            for (var i = 0; i < this.state.layerData.adb_themes.length; i++) {
                if (i == this.state.layerData.adb_themes.length - 1) {
                    catList.push(<span key={this.state.layerData.adb_themes[i].code}>{this.state.layerData.adb_themes[i].name} ({this.state.layerData.adb_themes[i].code})</span>)
                }
                else {
                    catList.push(<span key={this.state.layerData.adb_themes[i].code}>{this.state.layerData.adb_themes[i].name} ({this.state.layerData.adb_themes[i].code}),</span>)
                }
            }

            return (
                <li id={"legend-item-" + this.props.layerid} layername={this.props.layerid} className="uk-open uk-padding-small uk-background-muted">
                    <a className="uk-accordion-title uk-text-small uk-text-bolder" href="#"><span className="uk-sortable-handle uk-margin-small-right uk-text-center" data-uk-icon="icon: table"></span>{this.state.layerData.title}</a>
                    <div className="uk-accordion-content uk-text-small">
                        <ul className="uk-iconnav">
                            <li><a data-uk-icon="icon: info" href={"#modal_layerlegend_" + this.props.layerid} data-uk-tooltip="title: Layer details; pos: bottom" data-uk-toggle=""></a></li>
                            <li><a href="#" onClick={this.handleZoomExtentClick} data-uk-icon="icon: search" data-uk-tooltip="title: Zoom to extent; pos: bottom"></a></li>
                            <li><a className={classicon} href="#" onClick={this.handleHideClick} data-uk-icon="icon: ban" data-uk-tooltip="title: Toggle visibility; pos: bottom"></a></li>
                            <li><a href="#" onClick={this.handleDelete} data-uk-icon="icon: trash" data-uk-tooltip="title: Remove; pos: bottom"></a></li>
                            <li><a href={this.state.layerData.detail_url} data-uk-icon="icon: cloud-download" data-uk-tooltip="title: Download layer; pos: bottom" target="_blank" rel="noreferrer noopener"></a></li>
                        </ul>
                        <div className="uk-margin">
                            <input className="uk-range" type="range" min="0" max="100" step="10" defaultValue="100" onChange={this.handleOpacityChange} data-uk-tooltip={"Opacity"}></input>
                        </div>
                        <div id={"modal_layerlegend_" + this.props.layerid} className="uk-flex-top uk-modal-container" data-uk-modal>
                            <div className="uk-modal-dialog uk-modal-body uk-margin-auto-vertical">
                                <h2 className="uk-modal-title">{this.state.layerData.title}</h2>
                                <div className="uk-flex-middle" data-uk-grid>
                                    <div className="uk-width-2-3@m uk-padding-small">
                                        <ul className="uk-iconnav">
                                            <li><a href={this.state.layerData.detail_url} data-uk-icon="icon: cloud-download" data-uk-tooltip="Download layer" target="_blank" rel="noreferrer noopener"></a></li>
                                        </ul>
                                        <p><span className="uk-text-bold">Categories: </span>{catList}</p>
                                        <p><span className="uk-text-bold uk-text-capitalize"> {this.state.layerData.date_type} date: </span> {this.state.layerData.date}</p>
                                        <p><span className="uk-text-bold">Source: </span>{this.state.layerData.raw_supplemental_information}</p>
                                        <p><span className="uk-text-bold">Description: </span>{this.state.layerData.raw_abstract}</p>
                                        <button className="uk-modal-close-default" type="button" data-uk-close></button>
                                    </div>
                                    <div className="uk-width-1-3@m uk-flex-first">
                                        <ImgPlus src={this.state.thumbnail_url} width="500" height="500" alt="Layer thumbnail"></ImgPlus>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div data-uk-tooltip="Click to enlarge" data-uk-lightbox>
                            <a data-type="image" href={DOMAIN_NAME_FULL + "geoserver/ows?&LAYER=" + this.state.layerData.alternate + "&SERVICE=WMS&REQUEST=GetLegendGraphic&FORMAT=image/png&transparent=false&format=image/png&LEGEND_OPTIONS=forceLabels:on;dpi=91;"} >
                                <ImgPlus src={DOMAIN_NAME_FULL + "geoserver/ows?&LAYER=" + this.state.layerData.alternate + "&SERVICE=WMS&REQUEST=GetLegendGraphic&FORMAT=image/png&transparent=true&format=image/png&LEGEND_OPTIONS=forceLabels:on;dpi=91;"} width="500" height="500" alt="Legend"></ImgPlus>
                            </a>
                        </div>
                    </div>
                </li>);
        }
        else if (this.state.status == 'loading') {
            return (
                <li id={"legend-item-" + this.props.layerid} layername={this.props.layerid} className="uk-open uk-background-muted uk-padding-small">
                    <a className="uk-accordion-title uk-text-small uk-text-secondary" href="#"><div data-uk-spinner></div>&nbsp;&nbsp;&nbsp;Loading...</a>
                    <div className="uk-accordion-content uk-text-small">
                        <p><span data-uk-spinner className="uk-padding"></span>&nbsp;&nbsp;&nbsp;Data loading...</p>
                    </div>
                </li>
            )
        }
        else {
            return null
        }
    }

}

// FILTER - SELECT LIST
class SelectGroupTree extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            rcode:'',
            ccode:'',
            scode:'',
            filterByMapExtent:true,
        };
        this.handleChange = this.handleChange.bind(this);
        this.handleChangeChk = this.handleChangeChk.bind(this);
    }

    handleChange(evt, filter) {

        // Setting the new filter value
        var current_state = this.state
        console.log(evt.target.value)
        current_state[filter] = evt.target.value
        
        // Case region is reset
        if(filter=='rcode'){
            current_state['ccode']=''
        }

        // Set state to refresh element
        this.setState(current_state)

        // Update layer filters
        mainFilterManager.setFilter(filter, evt.target.value)

    }

    handleChangeChk(){

        // Changing layer state
        var current_state = this.state
        current_state['filterByMapExtent'] = !current_state['filterByMapExtent']
        if(current_state['filterByMapExtent']){
            this.setState({
                rcode: '',
                ccode: '',
                scode: '',
                filterByMapExtent: true,
            })
        }
        else (
            this.setState(current_state)
        )

        // TODO: Refresh layer filters
        mainFilterManager.toggleBBOXFilterActive()
    }

    
    render(){
        var geospatdivision_filters = []

        if(this.state.filterByMapExtent){
            geospatdivision_filters = []
        }
        else {
            geospatdivision_filters.push(
                < SelectList
                    id="region"
                    src='api/spade/adb_geospatdivision/region/'
                    verbose_name='Select region'
                    code_field='rcode'
                    name_field='rname'
                    handleChange={this.handleChange} >
                </SelectList >
            )

            if (this.state.rcode != '') {
                geospatdivision_filters.push(
                    <SelectList
                        id="country"
                        key={'adb_GeospatdivisionCountry_' + this.state.rcode}
                        src='api/spade/adb_geospatdivision/country/'
                        verbose_name='Select country'
                        code_field='ccode'
                        name_field='cname'
                        filter={this.state.rcode}
                        handleChange={this.handleChange}>
                    </SelectList>
                )
            }

            if (this.state.ccode != '') {
                geospatdivision_filters.push(
                    <SelectList
                        id="subdivision"
                        key={'adb_GeospatdivisionSubdivision_' + this.state.rcode + '_' + this.state.ccode}
                        src='api/spade/adb_geospatdivision/subdivision/'
                        verbose_name='Select subdivision'
                        code_field='scode'
                        name_field='sname'
                        filter={this.state.ccode}
                        handleChange={this.handleChange}>
                    </SelectList>
                )
            }
        }
        


        return (
            <div className="uk-width-1-1 uk-margin-small-bottom">   
                <div className="uk-margin-remove">
                    <label className="uk-form-small uk-padding-remove"><input className="uk-checkbox" type="checkbox" onClick={this.handleChangeChk} defaultChecked={this.state.filterByMapExtent}/> Map extent</label>
                </div>
                <div className="uk-margin-remove">
                    {geospatdivision_filters}
                </div>
            </div>
        )
    }
}

class SelectList extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            status:'loading',
            rcode: '',
            ccode: '',
            choices: {},
        };
    } 

    componentDidMount() {
        var url = new URL(DOMAIN_NAME_FULL + this.props.src)
        url.searchParams.append('filter', this.props.filter)
        fetch(url)
            .then(res => res.json())
            .then(
                (result) => {
                    this.setState({
                        status:'ready',
                        choices:result,
                    })
                },
                (error) => {
                    UIkit.notification('Error loading filter: ' + this.props.verbose_name, 'danger');
                    this.setState({
                        status: 'error',
                        error
                    });
                }
            )
    }

    render() {

        // Loading option parameters
        var list_items = []
        for (var i = 0; i < this.state.choices.length; i++) {
            var item = this.state.choices[i];
            list_items.push(<option key={item[this.props.code_field]} value={item[this.props.code_field]}>{item[this.props.name_field]}</option>)
        }
        
        if (this.state.status == 'ready'){
            return (    
                <form>
                    <fieldset className="uk-fieldset">
                        <div className="uk-margin-small-bottom">
                            <select id={this.props.id + "_filter"} className="uk-select uk-form-small" onChange={evt => this.props.handleChange(evt, this.props.code_field)}>
                                <option value="">{this.props.verbose_name}</option>
                                {list_items}
                            </select>
                        </div>
                    </fieldset>
                </form>
            )
        }

        else {

            return (
                <form>
                    <fieldset className="uk-fieldset">
                        <div className="uk-margin-small-bottom">
                            <p><span data-uk-spinner></span>&nbsp;&nbsp;&nbsp;Loading...</p>
                        </div>
                    </fieldset>
                </form>
            )
        }
        
    }
}

// FILTER - SELECT MULTIPLE LIST
class SelectMultipleList extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            status: 'loading',
            choices: {},
        };
    }

    componentDidMount() {
        fetch(DOMAIN_NAME_FULL + "api/spade/" + this.props.id + "/")
            .then(res => res.json())
            .then(
                (result) => {
                    this.setState({
                        status: 'ready',
                        choices: result,
                    })
                },
                (error) => {
                    UIkit.notification('Error loading filter: ' + this.props.verbose_name, 'danger');
                    this.setState({
                        status: 'error',
                        error
                    });
                }
            )
    }

    render() {

        // Loading option parameters
        var list_items = []
        for (var i = 0; i < this.state.choices.length; i++) {
            var item = this.state.choices[i];
            list_items.push(
                <SelectMultipleListItem key={item["id"]} code={item["code"]} parent={this.props.id} icon={item["icon"]} name={item["name"]} item_id={item["id"]}></SelectMultipleListItem>
            )
        }

        if (this.state.status == 'ready') {
            return (
                <div className="uk-margin-remove uk-grid-small uk-child-width-auto uk-grid uk-width-1-1">
                    {list_items}
                </div>
            )
        }

        else {

            return (
                <div className="uk-margin-remove uk-grid-small uk-child-width-auto uk-grid uk-width-1-1">
                    <p><span data-uk-spinner></span>&nbsp; Loading...</p>
                </div>
            )
        }

    }
}

// FILTER - SELECT MULTIPLE LIST ITEMS
class SelectMultipleListItem extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            active:false,
            class:"spade-custom-theme-icon",
        };

        this.handleClick = this.handleClick.bind(this);
    }
      
    handleClick(){
        var item_id = this.props.item_id
        var filter_parent = this.props.parent
        var filter_value_current = mainFilterManager.url.searchParams.get(this.props.parent)

        if (this.state.active){$
            this.setState({ 
                active: false,
            })
            var filter_value = filter_value_current.split(',').filter(function (value) { return value != item_id }).toString();
        }
        // Filter ON
        else {
            //mainFilterManager.setFilter(this.props.parent, filter_value)
            this.setState({
                active: true,
            })

            if (filter_value_current == null || filter_value_current == '' ){
                var filter_value = item_id
            }
            else {
                var filter_value = filter_value_current.split(',')
                filter_value.push(item_id)
            }
        }
        mainFilterManager.setFilter(filter_parent, filter_value)
    }

    render() {

        // Loading option parameters
       
        if(this.state.active){
            var itemDom = <img className="uk-icon-image spade-custom-theme-icon-selected" src={this.props.icon} width="20px" height="20px" data-uk-svg="" ></img>
        }
        else {
            var itemDom = <img className="uk-icon-image spade-custom-theme-icon" src={this.props.icon} width="20px" height="20px" data-uk-svg="" ></img>
        }


        return (
            <div className="uk-padding-small uk-padding-remove-top uk-padding-remove-left" >
                <div className="uk-margin uk-grid-small uk-child-width-auto uk-grid" data-uk-tooltip={this.props.name + " (" + this.props.code + ")"}>
                    <label><input onClick={this.handleClick} className="uk-checkbox" type="checkbox"></input>&nbsp; {itemDom}</label>
                </div>
                
            </div>
        )
    }
}

// FILTER - SEARCH BAR
class SearchBar extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
        };

    }

    handleChange(evt) {
        const filter_key = this.props.id
        const filter_value = evt.target.value;

        // Updating filter options
        if (evt.target.value == ''){
            mainFilterManager.deleteFilter(filter_key)
        }
        else {
            mainFilterManager.setFilter(filter_key, filter_value)
        }
    }

    render() {
        return (
            <form className="uk-search uk-search-default uk-width-1-1 uk-margin-remove">
                <span  data-uk-search-icon></span>
                <input
                    className="uk-search-input"
                    type="search"
                    placeholder={this.props.verbose_name}
                    onChange={evt => this.handleChange(evt)}>
                </input>
            </form>

        )
    }
}

// RESULTS - RESULT LIST
class ResultList extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            status: 'loading',
            results:[]
        };

    }

    componentDidMount() {
        fetch(mainFilterManager.url.toString())
            .then(res => res.json())
            .then(
                (result) => {
                    this.setState({
                        status:'ready',
                        results:result
                    })
                },
                (error) => {
                    UIkit.notification('Error retrieving datasets results from server', 'danger');                    
                    this.setState({
                        status: 'error',
                        error
                    });
                }
            )
    }

    render() {

        var resultlist_items = []

        for (var i = 0; i < this.state.results.length; i++) {
            var result_item = this.state.results[i];
            resultlist_items.push(
                <ResultItem key={result_item.pk} pk={result_item.pk}></ResultItem>
            )
        }
        
        var resultlist_title
        if(this.state.status == 'ready'){
            resultlist_title = <p className="uk-text-default uk-text-middle uk-margin-small-top uk-margin-small-bottom"> {this.state.results.length} Results</p>
        }
        else {
            resultlist_title = <p className="uk-text-default uk-text-middle uk-margin-small-top uk-margin-small-bottom"><span data-uk-spinner uk-spinner="ratio: 0.8" className="uk-padding-remove"></span> &nbsp; Loading results...</p>
        }

        return (
            <div className="uk-margin-small-left" >
                {resultlist_title}
                <div className="spade-custom-scroller uk-padding-small uk-padding-remove-bottom" style={{height:'calc(100vh - 300px)'}}>
                    {resultlist_items}
                </div>
            </div>

        )
    }
}


// RESULTS - RESULT LIST ITEMS
class ImgPlus extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            status: 'loading',
        };
        this.handleOnLoad = this.handleOnLoad.bind(this);
    }

    handleOnLoad(){
        console.log('loaded')
        this.setState({ status:'ready'})
    }

    render() {
        var spinnerDom = []

        var altText = ''
        if (this.props.alt != ''){
            var altText = this.props.alt
        }
        else {
            altText = 'Image'
        }

        if(this.state.status == 'loading'){
            spinnerDom.push(
                <p className="uk-padding-small uk-margin-remove uk-text-small"><span data-uk-spinner="ratio: 0.8"></span> &nbsp; {altText} loading...</p>
            )
        }
        else{ spinnerDom = []}

        var domRes = (
            <div className="uk-width-1-1 uk-height-1-1">
                <img src={this.props.src} onLoad={this.handleOnLoad}/>
                {spinnerDom}
            </div>
        )

        return domRes
    }

}

// RESULTS - RESULT LIST ITEMS
class ResultItem extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            status:'loading',
            layerData: {}
        };
        this.handleLayerAdd = this.handleLayerAdd.bind(this);
        this.handleMouseEnter = this.handleMouseEnter.bind(this);
        this.handleMouseLeave = this.handleMouseLeave.bind(this);
    }

    
    componentDidMount() {
        fetch(DOMAIN_NAME_FULL + "api/spade/resource_detail/"+this.props.pk+"/")
        .then(res => res.json())
        .then(
            (result) => {
                // Getting Layer coordinates from WMS servcie
                fetch(DOMAIN_NAME_FULL+"capabilities/layer/" + this.props.pk + "/")
                .then(xml_text => xml_text.text())
                .then(
                            (xml_text) => {
                                
                                var parser = new DOMParser();
                                var xmlDoc = parser.parseFromString(xml_text, "text/xml");
                                var coordsXML = xmlDoc.getElementsByTagName("EX_GeographicBoundingBox")[0].children
                                var bbox_coords_correct = [
                                    [parseFloat(coordsXML[2].innerHTML), parseFloat(coordsXML[0].innerHTML)],
                                    [parseFloat(coordsXML[2].innerHTML), parseFloat(coordsXML[1].innerHTML)],
                                    [parseFloat(coordsXML[3].innerHTML), parseFloat(coordsXML[1].innerHTML)],
                                    [parseFloat(coordsXML[3].innerHTML), parseFloat(coordsXML[0].innerHTML)],
                                    [parseFloat(coordsXML[2].innerHTML), parseFloat(coordsXML[0].innerHTML)],
                                ]
                                
                                // Setting the layer polygon extent
                                var bbox_polygon = L.polygon(bbox_coords_correct)
                                bbox_polygon.setStyle({
                                    color: "red",
                                    opacity: 0.5,
                                    fillColor: "red",
                                    fillOpacity: 0.3
                                });

                                // Setting the layer center marker
                                var icon = L.icon({
                                    iconUrl: '/static/gdc/img/layer_position_icon.png',
                                    iconSize: [30, 30],
                                    iconAnchor: [15, 15],
                                });
                                var bbox_center = L.marker(bbox_polygon.getBounds().getCenter(), { icon: icon })
                                
                                // Setting title nicer
                                result.title = toTitleCase(result.title.replaceAll('_', ' '))

                                // Setting date nicer
                                var options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
                                var date_refactor = new Date(result.date)
                                result.date = date_refactor.toLocaleDateString("en-US", options)
                                
                                // Getting thumbnail depending on custom thumbnail availability
                                if(result.curatedthumbnail != null){
                                    var thumbnail_url = DOMAIN_NAME_FULL + result.curatedthumbnail.thumbnail_url.toString()
                                }
                                else {
                                    var thumbnail_url = result.thumbnail_url
                                }

                                result.detail_url = DOMAIN_NAME_FULL + result.detail_url.toString()

                                // Changing state of react component
                                this.setState({
                                    status: 'ready',
                                    layerData: result,
                                    bbox: bbox_polygon,
                                    bbox_center: bbox_center,
                                    thumbnail_url: thumbnail_url
                                })
                            }
                            )
                },
                (error) => {
                    UIkit.notification('Error retrieving datasets results from server', 'danger');
                    this.setState({
                        status: 'error',
                        error
                    });
                }
            )
        }
        
    componentWillUnmount() {
        //this.state.bbox.remove()
        //this.state.bbox_center.remove()
    }

    handleLayerAdd(){
        legendComponent.addLegendItem(this.props.pk)
        openLegendPanel()
    }

    handleMouseEnter() {
        this.state.bbox.addTo(map)
        this.state.bbox_center.addTo(map)
    }

    handleMouseLeave(){
        this.state.bbox.remove()
        this.state.bbox_center.remove()
    }


    render() {        
        if (this.state.status == 'ready') {

            var catList = []
            for (var i = 0; i < this.state.layerData.adb_themes.length; i++){
                if(i == this.state.layerData.adb_themes.length-1){
                    catList.push(<span key={this.state.layerData.adb_themes[i].code}>{this.state.layerData.adb_themes[i].name} ({this.state.layerData.adb_themes[i].code})</span>)
                }
                else {
                    catList.push(<span key={this.state.layerData.adb_themes[i].code}>{this.state.layerData.adb_themes[i].name} ({this.state.layerData.adb_themes[i].code}),</span>)
                }
            }

            var domToRender = (
                <div key={this.props.pk} className=" uk-animation-fade uk-margin-small-bottom uk-padding-small uk-card uk-card-default uk-card-body uk-card-hover " onMouseEnter={this.handleMouseEnter} onMouseLeave={this.handleMouseLeave} >
                    <p className="uk-margin-small uk-text-small uk-text-bolder">{this.state.layerData.title}</p>
                    <ul className="uk-margin-small uk-iconnav">
                        <li><a href={"#modal_layerresult_" + this.props.pk} data-uk-tooltip="Display layer information" data-uk-icon="icon: info" data-uk-toggle=""></a></li>
                        <li><a href={this.state.layerData.detail_url} data-uk-icon="icon: cloud-download" data-uk-tooltip="Download layer" target="_blank" rel="noreferrer noopener"></a></li>
                        <li><a data-uk-icon="icon: plus" data-uk-tooltip="Add layer to map" onClick={this.handleLayerAdd}></a></li>
                    </ul>

                    <div className="uk-padding-remove uk-grid-small" data-uk-grid>
                        <div className="uk-width-2-5@xl">
                            <ImgPlus src={this.state.thumbnail_url} width="500" height="500" alt="Layer thumbnail"></ImgPlus>
                        </div>
                        <div className="uk-width-3-5@xl">
                            <p className="uk-text-justify uk-text-small">{this.state.layerData.raw_abstract.substring(0, 150)}...</p>
                        </div>
                    </div>

                    <div id={"modal_layerresult_" + this.props.pk} className="uk-flex-top uk-modal-container" data-uk-modal>
                        <div className="uk-modal-dialog uk-modal-body uk-margin-auto-vertical">
                            <h2 className="uk-modal-title">{this.state.layerData.title}</h2>
                            <div className="uk-flex-middle" data-uk-grid>
                                <div className="uk-width-2-3@m uk-padding-small">
                                    <ul className="uk-iconnav">
                                        <li><a href={this.state.layerData.detail_url} data-uk-icon="icon: cloud-download" data-uk-tooltip="Download layer" target="_blank" rel="noreferrer noopener"></a></li>
                                    </ul>
                                    <p><span className="uk-text-bold">Categories: </span>{catList}</p>
                                    <p><span className="uk-text-bold uk-text-capitalize"> {this.state.layerData.date_type} date: </span> {this.state.layerData.date}</p>
                                    <p><span className="uk-text-bold">Source: </span>{this.state.layerData.raw_supplemental_information}</p>
                                    <p><span className="uk-text-bold">Description: </span>{this.state.layerData.raw_abstract}</p>
                                    <button className="uk-modal-close-default" type="button" data-uk-close></button>
                                </div>
                                <div className="uk-width-1-3@m uk-flex-first">
                                    <img src={this.state.thumbnail_url} width="500" height="500" alt="Image"></img>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )
        }
        else {
            var domToRender = (
                <p className="uk-animation-fade uk-padding-small uk-text-small uk-text-bolder"><span data-uk-spinner className="uk-padding-remove"></span>&nbsp; &nbsp; &nbsp;Result loading...</p>
            )

        }
        return domToRender
    }
}


// =========================================================================================================================
// ================================================ FILTER MANAGER =========================================================
// =========================================================================================================================

// Class used to manage and refresh URL filters
class FilterManager {
    constructor(){
        this.url = new URL(DOMAIN_NAME_FULL + "api/spade/resource_list/")
        this.bboxFilterActive = true
        this.bboxFilterValue = ''
    }

    toggleBBOXFilterActive(){
       
        this.bboxFilterActive = !this.bboxFilterActive
        if(this.bboxFilterActive){
            this.url.searchParams.delete('rcode')
            this.url.searchParams.delete('ccode')
            this.url.searchParams.delete('scode')
            this.url.searchParams.append('bbox', this.bboxFilterValue)
            console.log(this.url.toString())
        }
        else{
            this.url.searchParams.delete('bbox')
        }
        this.applyFilters()
    }

    getFilter(filter_key){
        return this.url.searchParams[filter_key]
    }

    setBBOXFilter(filter_value) {
        var filter_key = 'bbox'
        this.bboxFilterValue = filter_value
        // The bbox filter is refreshed only if bboxFilterActive is set to "true"
        if (this.bboxFilterActive){
            this.url.searchParams.delete(filter_key)
            this.url.searchParams.append(filter_key, filter_value)
            this.applyFilters()
            return true
        }
    }

    setFilter(filter_key, filter_value){
        // specific handler for bbox filter
        if(filter_key == 'bbox'){
            this.setBBOXFilter(filter_value)
            return true
        }
        else {
            this.url.searchParams.delete(filter_key)
            this.url.searchParams.append(filter_key, filter_value)
            this.applyFilters()
            return true
        }
    }

    deleteFilter(filter_key) {
        this.url.searchParams.delete(filter_key)
        this.applyFilters()
        return true
    }

    applyFilters(){
        fetch(this.url)
            .then(
                function(res){
                    try {
                        return res.json()
                    }
                    catch (error) {
                        return null
                    }
                }
            )
            .then(
                (result) => {
                    if( result != null){
                        mainResultList.setState({
                            status: 'ready',
                            results: result
                        })
                    }
                },
                (error) => {
                    UIkit.notification('Error retrieving datasets results from server', 'danger');
                    mainResultList.setState({
                        status: 'error',
                        error
                    });
                }
            )
        
        


    }


}

// =========================================================================================================================
// ================================================ LEAFLET LAYER MANAGER ==================================================
// =========================================================================================================================

// Class used to manage layer order and loading in leaflet
class LayerManager {

    constructor(map) {
        this.parentMap = map
        this.layers = {}
    }

    setLayerOpacity(layerKey, opacity){
        this.layers[layerKey].opacity = opacity
        this.layers[layerKey].opacityOld = opacity
        this.layers[layerKey].layerLeaflet.setOpacity(opacity / 100)
    }

    toggleMapLayerVisibility(layerKey) {
        if (this.layers[layerKey].opacity !== 0){
            this.layers[layerKey].opacity = 0
            this.layers[layerKey].layerLeaflet.setOpacity(this.layers[layerKey].opacity / 100)
        }
        else {
            this.layers[layerKey].opacity = this.layers[layerKey].opacityOld
            this.layers[layerKey].layerLeaflet.setOpacity(this.layers[layerKey].opacity / 100)
        }
    }

    addMapLayer(layerAlternateName, layerKey){

        // Get layer name
        var wmsOptions = {
            layers: layerAlternateName,
            transparent: true,
            format: 'image/png',
            maxZoom: 20,
        }
        var layerLeaflet = L.tileLayer.wms(DOMAIN_NAME_FULL +'/geoserver/ows?', wmsOptions).addTo(map);
        layerLeaflet.setOpacity(100)

        this.layers[layerKey] = {
            "layerLeaflet": layerLeaflet,
            "opacity": 100,
            "opacityOld": 100
        }
        this.reloadMapLayers()
    }

    removeMapLayer(layerKey){
        this.parentMap.removeLayer(this.layers[layerKey].layerLeaflet)
        delete this.layers[layerKey]
    }

    reloadMapLayers(){
        // try {
            // Get last layers order from legend
            var layers_to_load = []
            for (let child of document.querySelector('#legend_main_container').children) {
                var childid = $('#' + child.id).attr('layername')
                if (childid !== "undefined") {
                    layers_to_load.push(childid)
                }
            }
            layers_to_load = layers_to_load.reverse()

            // Unloading layers
        
            for (let layer_to_unload in this.layers) {
                if (typeof this.layers[layer_to_unload] !== 'undefined'){
                    getMap().removeLayer(this.layers[layer_to_unload].layerLeaflet)   
                }
            }

            // Loading layers in the correct order
            
            for (let layer_to_load of layers_to_load) {
                if (typeof this.layers[layer_to_load] !== 'undefined') {
                    this.layers[layer_to_load].layerLeaflet.addTo(this.parentMap)
                }
            }

            
            return true;
        // }
        // catch (error) {
        //     UIkit.notification('Error refreshing layers ('+error+')', 'danger');
        //     return false;
        // }
    }
}

// ===========================================================================================================================
// ================================================ LEAFLET CUSTOM CONTROLS ==================================================
// ===========================================================================================================================

// LEAFLET CUSTOM BUTTON
var legendPanelToggle = L.Control.extend({

    options: {
        position: 'topright',
    },

    onAdd: function () {
        var container = L.DomUtil.create('input', "uk-text-bolder spade-custom-leaflet-button spade-custom-leaflet-button-right");
        container.type = "button";
        container.title = "No cat";
        container.value = "        Legend >   ";

        container.onclick = function () {
            togglePanel("right")
        }

        return container;
    }
});

var searchPanelToggle = L.Control.extend({

    options: {
        position: 'topleft',
    },

    onAdd: function () {
        var container = L.DomUtil.create('input', "uk-text-bolder spade-custom-leaflet-button spade-custom-leaflet-button-left");
        <a href="#" onClick={this.handleDelete} uk-icon="icon: trash"></a>
        container.type = "button";
        container.title = "No cat";
        container.value = "   < Search        ";

        container.onclick = function () {
            togglePanel("left")
        }

        return container;
    }
});

// ==================================================================================================================
// ================================================ UTILITIES =======================================================
// ==================================================================================================================

function toTitleCase(str) {
    return str.replace(
        /\w\S*/g,
        function (txt) {
            return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
        }
    );
}


// ==================================================================================================================
// ================================================ MAIN JS SCRIPT ==================================================
// ==================================================================================================================

// Global variables
var DOMAIN_NAME = 'geonode.spade-staging.egis-eau-sas.fr'
var DOMAIN_NAME_FULL = 'https://'+DOMAIN_NAME+'/'
//window.location.hostname

// Preventing form submission
$(document).ready(function () {
    $(window).keydown(function (event) {
        if (event.keyCode == 13) {
            event.preventDefault();
            return false;
        }
    });
});

// LEAFLET COMPONENTS
var map = L.map('map', { attributionControl: true, zoomControl: false })

// Setting map center
map.setView([14.5965788, 120.9445403], 4);

// Map boundary
var southWest = L.latLng(-90, -180), northEast = L.latLng(90, 180);
var bounds = L.latLngBounds(southWest, northEast);
map.setMaxBounds(bounds)

// Map Min Zoom
map.options.minZoom = 2;

// Adding custom controls to map
map.addControl(new legendPanelToggle());
L.control.zoom({ position: 'topright' }).addTo(map);
map.addControl(new searchPanelToggle());
map.addControl(new L.Control.loading()); 

// Layer manager
var mainLayerManager = new LayerManager(map)

function getMap(){
    return map;
}

// Base layer switcher
new L.basemapsSwitcher([
    {
        layer: L.tileLayer('https://maps.geoapify.com/v1/tile/positron/{z}/{x}/{y}.png?apiKey=2b192eb2767d4af0926ad644aa3dce46', {
            attribution: 'Powered by <a href="https://www.geoapify.com/" target="_blank">Geoapify</a> | <a href="https://openmaptiles.org/" target="_blank">© OpenMapTiles</a> <a href="https://www.openstreetmap.org/copyright" target="_blank">© OpenStreetMap</a> contributors',
            maxZoom: 20, 
            id: 'osm-grey'
        }).addTo(map), //DEFAULT MAP
        icon: '/static/gdc/img/img0.PNG',
        name: 'OSM Grey'
    },

    {
        layer: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 20,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }), //DEFAULT MAP
        icon: '/static/gdc/img/img1.PNG',
        name: 'OSM Base'
    },
    
    {
        layer: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            maxZoom: 20,
            attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="https://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
        }),
        icon: '/static/gdc/img/img3.PNG',
        name: 'OSM Topo'
    },
    {
        layer: L.tileLayer('https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
            maxZoom: 20,
            subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
            attribution: 'Données cartographiques ©2022 Google'
        }),
        icon: '/static/gdc/img/img4.PNG',
        name: 'G. Streets'
    },
    {
        layer: L.tileLayer('https://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}', {
            maxZoom: 20,
            subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
            attribution: 'Données cartographiques ©2022 Google'
        }),
        icon: '/static/gdc/img/img6.PNG',
        name: 'G. Hybrid'
    },
    {
        layer: L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
            maxZoom: 20,
            subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
            attribution: 'Données cartographiques ©2022 Google'
        }),
        icon: '/static/gdc/img/img5.PNG',
        name: 'G. Satellite'
    },
], { position: 'bottomright' }).addTo(map);

// Filter manager
var mainFilterManager = new FilterManager()
map.on('moveend', function (e) {
    var bounds = map.getBounds().toBBoxString();
    mainFilterManager.setFilter('bbox', bounds)
});
var bounds = map.getBounds().toBBoxString();
mainFilterManager.setFilter('bbox', bounds)

// Addition of date picker
var selectedDatesMain = []
flatpickr(
    '#flatpickr-after', {
        enableTime: false,
        onChange: function (selectedDates, dateStr, instance) {
            console.log(selectedDates.length)
            selectedDatesMain = selectedDates
            if (selectedDates.length == 1){
                mainFilterManager.setFilter('date_begin', selectedDates[0].toISOString().substring(0, 10))
            }
            else {
                mainFilterManager.deleteFilter('date_begin')
            }
            mainFilterManager.applyFilters()
        },
    }
);
flatpickr(
    '#flatpickr-before', {
    enableTime: false,
    onChange: function (selectedDates, dateStr, instance) {
        console.log(selectedDates.length)
        selectedDatesMain = selectedDates
        if (selectedDates.length == 1) {
            mainFilterManager.setFilter('date_end', selectedDates[0].toISOString().substring(0, 10))
        }
        else {
            mainFilterManager.deleteFilter('date_end')
        }
        mainFilterManager.applyFilters()
    },
}
);

// Addition of REACT Components
var legendComponent = ReactDOM.render(
    <Legend id='legend_main_container'></Legend>, 
    document.querySelector('#legend_container')
);
var adbGeospatdivisionRegionFilter = ReactDOM.render(
   <SelectGroupTree></SelectGroupTree>,
   document.querySelector('#adb_geospatdivision_filter_container')
);
var adbThemeFilter = ReactDOM.render(
    <SelectMultipleList id='adb_themes' verbose_name='Data theme'></SelectMultipleList>,
    document.querySelector('#adb_theme_filter_container')
);
var adbSearchFilter = ReactDOM.render(
    <SearchBar id='search' verbose_name='Search layer name'></SearchBar>,
    document.querySelector('#search_filter_container')
);
var mainResultList = ReactDOM.render(
    <ResultList id='mainResultList'></ResultList>,
    document.querySelector('#result_container')
);





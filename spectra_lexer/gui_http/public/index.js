var state = {};
// Add all URL query items as JSON-format state variables.
var queryParams = new URLSearchParams(window.location.search);
for (let p of queryParams){
    try{
        state[p[0]] = JSON.parse(p[1]);
    }catch(e){
        console.error(e);
    }
}

$(document).ready(function(){
    class ListHandler {
        constructor(id, statevar, action) {
            this.active = {};
            this.root = document.getElementById(id);
            this.root.addEventListener("click", this.event.bind(this));
            this.statevar = statevar;
            this.action = action;
        }
        selectElem(elem){
            if(this.root === elem || this.active === elem){
                return false;
            }
            this.active.className = "";
            this.active = elem;
            elem.className = 'selected';
            return true;
        }
        selectText(value){
            for (let elem of this.root.children){
                if(elem.textContent == value){
                    this.selectElem(elem);
                }
            }
            return true;
        }
        event(evt){
            var elem = evt.target
            if(this.selectElem(elem)){
                state[this.statevar] = elem.textContent;
                processAction(this.action);
            }
        }
        update(optArray){
            this.active = {};
            var root = this.root;
            while (root.hasChildNodes()) {
                root.removeChild(root.firstChild);
            }
            for (let opt of optArray){
                var item = document.createElement("li");
                item.textContent = opt;
                root.appendChild(item);
            }
        }
    }
    const matchSelector = new ListHandler("w_search_matches",  "match_selected", "VIEWLookup");
    const mappingSelector = new ListHandler("w_search_mappings",  "mapping_selected", "VIEWSelect");

    const searchInput = document.getElementById("w_search_input");
    const displayTitle = document.getElementById("w_display_title");
    searchInput.addEventListener("input", function(){
        state.input_text = this.value;
        processAction("VIEWSearch");
    });
    displayTitle.addEventListener("input", function(){
        state.translation = this.value;
        processAction("VIEWQuery");
    });

    const searchType = document.getElementById("w_search_type");
    const searchRegex = document.getElementById("w_search_regex");
    searchType.addEventListener("change", function(){
        state.mode_strokes = this.checked;
        processAction("VIEWSearch");
    });
    searchRegex.addEventListener("change", function(){
        state.mode_regex = this.checked;
        processAction("VIEWSearch");
    });

    const displayLink = document.getElementById("w_display_link");
    const displayDesc = document.getElementById("w_display_desc");
    displayLink.addEventListener("click", function(){
        processAction("VIEWSearchExamples");
        return false;
    });

    const displayBoard = document.getElementById("w_display_board");
    function onBoardResize(){
        state.board_aspect_ratio = displayBoard.clientWidth / 250;
    }
    $(window).resize(onBoardResize);

    const displayText = document.getElementById("w_display_text");
    $("#w_display_text").on("mouseenter", "a.gg", function(){
        var ref = "#" + this.href.split("#").pop();
        if(state.graph_node_ref!=ref){
            state.graph_node_ref = ref;
            processAction("VIEWGraphOver");
        }
        return false;
    }).on("click", "a.gg", function(){
        processAction("VIEWGraphClick");
        return false;
    }).click(function(){
        state.graph_node_ref = "";
        processAction("VIEWGraphClick");
        return false;
    });

    var updateTable = {
        matches(value) {matchSelector.update(value);},
        match_selected(value) {matchSelector.selectText(value);},
        mappings(value) {mappingSelector.update(value);},
        mapping_selected(value) {mappingSelector.selectText(value);},
        input_text(value) {searchInput.value = value; return true;},
        translation(value) {displayTitle.value = value; return true;},
        link_ref(value) {displayLink.style.display = (value ? "" : "none"); return true;},
        board_caption(value) {displayDesc.textContent = value;},
        board_xml_data(value) {displayBoard.innerHTML = value;},
        graph_text(value) {displayText.innerHTML = value;},
    };
    function updateState(new_state){
        // Keep state variables that either return true on GUI update or don't update the GUI at all.
        for (let prop in updateTable){
            if(prop in new_state && !updateTable[prop](new_state[prop])){
               delete new_state[prop]
            }
        }
        for (let prop in new_state){
            state[prop] = new_state[prop];
        }
    }
    function processAction(action){
        $.ajax({
            method: 'POST',
            url: action,
            contentType: 'application/json',
            data: JSON.stringify(state),
            success: updateState,
            error() {displayDesc.innerHTML = '<span style="color: #d00000;">CONNECTION ERROR</span>'}
        });
    }

    // Before starting, save the initial board size and hide the link.
    onBoardResize();
    updateTable.link_ref("");
});

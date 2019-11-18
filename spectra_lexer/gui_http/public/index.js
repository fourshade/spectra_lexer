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
const titleDelim = " -> ";

$(document).ready(function(){
    class ListHandler {
        constructor(id, statevar, action) {
            this.active = {};
            this.root = document.getElementById(id);
            this.root.addEventListener("click", this.event.bind(this));
            this.statevar = statevar;
            this.action = action;
        }
        selectElem(elem) {
            if(this.root === elem || this.active === elem){
                return false;
            }
            this.active.className = "";
            this.active = elem;
            elem.className = 'selected';
            return true;
        }
        selectText(value) {
            for (let elem of this.root.children){
                if(elem.textContent == value){
                    return this.selectElem(elem);
                }
            }
        }
        event({target}) {
            if(this.selectElem(target)){
                state[this.statevar] = target.textContent;
                processAction(this.action);
            }
        }
        update(optArray) {
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
            if (optArray.length == 1){
                // Automatically select the item if there was only one.
                // FIXME: selects mappings twice
                this.event({target: item});
            }
        }
    }
    const matchSelector = new ListHandler("w_matches", "match_selected", "Lookup");
    const mappingSelector = new ListHandler("w_mappings", "mapping_selected", "Select");

    const searchInput = document.getElementById("w_input");
    const displayTitle = document.getElementById("w_title");
    searchInput.addEventListener("input", function(){
        state.input_text = this.value;
        processAction("Search");
    });
    displayTitle.addEventListener("input", function(){
        params = this.value.split(titleDelim)
        if(params.length == 2){
            state.translation = params.map(s => s.trim())
            processAction("Query");
        }
    });

    const searchModeStrokes = document.getElementById("w_strokes");
    const searchModeRegex = document.getElementById("w_regex");
    searchModeStrokes.addEventListener("change", function(){
        state.search_mode_strokes = this.checked;
        processAction("Search");
    });
    searchModeRegex.addEventListener("change", function(){
        state.search_mode_regex = this.checked;
        processAction("Search");
    });

    const displayLink = document.getElementById("w_link");
    const displayDesc = document.getElementById("w_desc");
    displayLink.addEventListener("click", function(){
        state.link_ref = this.href;
        processAction("SearchExamples");
        return false;
    });

    const displayBoard = document.getElementById("w_board");
    function onBoardResize(){
        state.board_aspect_ratio = displayBoard.clientWidth / 250;
    }
    $(window).resize(onBoardResize);

    const displayText = document.getElementById("w_text");
    $("#w_text").on("mouseenter", "a.gg", function(){
        var ref = this.href.split("#").pop();
        if(state.graph_node_ref != ref){
            state.graph_node_ref = ref;
            processAction("GraphOver");
        }
        return false;
    }).on("click", "a.gg", function(){
        processAction("GraphClick");
        return false;
    }).click(function(){
        state.graph_node_ref = "";
        processAction("GraphClick");
        return false;
    });
    var updateTable = {
        // These output variables do not need to be tracked. Since they can be large, they shouldn't be.
        matches(value) {matchSelector.update(value);},
        mappings(value) {mappingSelector.update(value);},
        page(value) {displayText.innerHTML = value.graph;
                     displayDesc.textContent = value.caption;
                     displayBoard.innerHTML = value.board;
                     displayLink.style.display = (value.rule_id ? "" : "none")
                     displayLink.href = value.rule_id;},
        // These output variables must be stored in the state for reference.
        input_text(value) {searchInput.value = value; return true;},
        match_selected(value) {matchSelector.selectText(value); return true;},
        mapping_selected(value) {mappingSelector.selectText(value); return true;},
        translation(value) {displayTitle.value = value.join(titleDelim); return true;},
    };
    function updateState(stateChanges){
        // Keep state variables that either return true on GUI update or don't update the GUI at all.
        for (let prop in updateTable){
            if(prop in stateChanges && !updateTable[prop](stateChanges[prop])){
               delete stateChanges[prop]
            }
        }
        for (let prop in stateChanges){
            state[prop] = stateChanges[prop];
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
    displayLink.style.display = "none"
});

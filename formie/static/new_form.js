let fields_div = document.getElementById('fields');

var index = 0;

function new_field() { 
	fields_div.insertAdjacentHTML('beforeend', `
<div id="field${index}">
	<input method="text" id="name" placeholder="Question"/>
	<select onchange="change_field(this.parentElement, this.value)">
		<option value="text">Text</option>
		<option value="single_choice">Single Choice</option>
		<option value="multi_choice">Multi Choice</option>
		<option value="range">Range</option>
	</select>
	<div id="extra"></div>
	<button onclick="this.parentElement.remove()">Remove field</button>
</div>`);
	change_field(fields_div.lastChild, "text");
	index++;
}

function change_field(field, typ) {
	let extra = field.children[field.children.length - 2];

	if (typ === "text") {
		extra.innerHTML = '<input method="text" id="default" placeholder="Default" />'; 
	} else if (typ === "single_choice") {
		extra.innerHTML = '<button onclick="add_choice(this.parentElement, true)">Add choice</button>';
	} else if (typ === "multi_choice") {
		extra.innerHTML = '<button onclick="add_choice(this.parentElement, false)">Add choice</button>';
	} else if (typ === "range") {
      extra.innerHTML = '<label>min</label><input class="range" type="text"/></input><label>max</label><input type="text"/></input><label>value</label><input type="text"></input>'
   }
}

function add_choice(element, is_radio) {
	var typ = 'checkbox';
	if (is_radio) typ = 'radio';
	element.insertAdjacentHTML('beforeend', `
<input type="${typ}"><input type="text"/></input>
`)
}

function make_schema() {
	let schema = [];
	for (field of fields_div.children) {
		let schema_field = {};
		schema_field.name = field.children[0].value;
		if ((field.children.length >= 3) && (field.children[2].children.length >= 2) && (field.children[2].children[1].className = "range")) {
			schema_field.type = "range";
			schema_field.min = field.children[2].children[1].value;
			schema_field.max = field.children[2].children[3].value;
			schema_field.default = field.children[2].children[5].value;
		} else if (field.children[1].selectedIndex === 0) {
			schema_field.type = "text";
			schema_field.default = field.children[2].lastChild.value;
		} else {
			schema_field.choices = [];
			schema_field.single = false;
			schema_field.type = "choice";
			schema_field.default = 0;
			if (field.children[1].selectedIndex === 1) schema_field.single = true;
			for (choice of field.children[2].children) {
				if (choice.tagName == 'INPUT' && choice.type == 'text') schema_field.choices.push(choice.value);
			}
		}
		schema.push(schema_field);
	}
	return schema;
}

function submit_form() {
	let req = new XMLHttpRequest();
	req.open('POST', document.location.href, false);
	req.setRequestHeader('Content-Type', 'application/json');
	req.send(JSON.stringify(make_schema()));
        window.location.href = '/';
}

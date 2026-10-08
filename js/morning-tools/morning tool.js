// ==UserScript==
// @name			Morning WOD Tools
// @namespace		Morning
// @version			1.02
// @description		WOD small tools
// @include			http*://*.world-of-dungeons.*/wod/spiel/*dungeon/report.php*
// @include			http*://*.world-of-dungeons.*/wod/spiel/tournament/*duell.php*
// @include			http*://*.world-of-dungeons.*/wod/spiel/trade/trade.php*
// @include			http*://*.world-of-dungeons.*/wod/spiel/hero/items.php*
// @updateURL		https://raw.githubusercontent.com/morningyet/my-wod-automation/master/js/morning-tools/morning%20tool.js
// @downloadURL		https://raw.githubusercontent.com/morningyet/my-wod-automation/master/js/morning-tools/morning%20tool.js
// ==/UserScript==
(function() {
	//filter report
	function filterMain() {
		function Factoryfilter(o) {
            return function() {
                filterReport(o);
            };
		}
		var tables = document.getElementsByTagName("table");
		for(var i= 0; i<tables.length; i++)
		{
			var table = tables[i];
			if(table.className == "rep_status_table")
			{
				for(var j=0;j<table.rows.length;j++)
				{
					var row = table.rows[j];
					for(var k=1;k<2;k++)
					{
						var cell = row.cells[k];
						if(cell.className == "hero")
						{
							var newCheckbox = document.createElement("input");
							newCheckbox.setAttribute("type", "checkbox");
							newCheckbox.setAttribute("class", "filter");
							newCheckbox.value = cell.firstChild.textContent;
							cell.insertBefore(newCheckbox, cell.firstChild);
							//newCheckbox.setAttribute("onclick", "test(this);");
							newCheckbox.addEventListener("click", Factoryfilter(newCheckbox), false);
							break;
						}
					}
				}
			}
		}
	}
	function filterReport(o)
	{
		var checkboxlist = document.getElementsByTagName("input");
		var selectedheros = [];
		var classNamepattern = /^[rep_monster|rep_hero|rep_myhero]/
		for(var i=0;i<checkboxlist.length;i++)
		{
			var checkbox = checkboxlist[i];
			if(checkbox.getAttribute("type") == "checkbox" && checkbox.getAttribute("class") == "filter")
            {
				if(checkbox.value == o.value)
					checkbox.checked = o.checked;
				if(checkbox.checked && selectedheros.indexOf(checkbox.value) <= -1)
					selectedheros.push(checkbox.value);
			}
		}
		var tables = document.getElementsByTagName("table");
		for(let i= 0; i<tables.length; i++)
		{
			var table = tables[i];
			if(table.className != "rep_status_table")
			{
				var istheTable = false;
				for(var j=0;j<table.rows.length;j++)
				{
					var row = table.rows[j];
					var show = false;
					if(row.cells.length <= 0)
                        continue;
                    if(row.cells[0].colSpan > 1)
                    {
						if(table.rows[j-1])
                            row.cells[0].style.display = table.rows[j-1].style.display;
                        continue;
                    }
					if(istheTable || row.cells[0].className == "rep_initiative")
					{
						istheTable = true;
						for(var k=1;k<2;k++)
						{
							var cell = row.cells[k];
							var links = cell.getElementsByTagName("a");
							for(var index =0;index < links.length;index++)
							{
								var link = links[index];
								if(classNamepattern.test(link.className))
								{
									var name = link.textContent;
									if(selectedheros.length <= 0 || selectedheros.indexOf(name) > -1)
									{
										show = true;
										break;
									}
								}
							}
							if(show)
								break;
						}
						row.style.display = show?'':'none';
					}
				}
			}
		}
	}	//reorder item type list
    function CompareString(a, b) {
        a = a.text ||"";
        b = b.text ||"";
        return a.toLowerCase().localeCompare(b.toLowerCase(),"zh-CN-u-co-pinyin");
    }	function sortList(select,skipNumber)
	{
		skipNumber = skipNumber||0
		var items = select.options.length;
		// create array and make copies of options in list
		var tmpArray = new Array(items - skipNumber);
		var selectedValue;
		for (let i=skipNumber; i<items; i++ )
		{
			tmpArray[i] = new Option(select.options[i].text,select.options[i].value,false,i== select.options.selectedIndex);
		}
		// sort options using given function
		tmpArray.sort(CompareString);
		// make copies of sorted options back to list
		for (let i=skipNumber; i<items; i++ )
		select.options[i] = tmpArray[i-skipNumber];
	}

	function reorderMain()
	{
		debugger;
		var itemtypepattern = /^item_\d+item_class$/;
		var itemsetpattern = /^item_\d+set$/;
		var selects = document.getElementsByTagName("select");
		for(var i = 0; i< selects.length;i++)
		{
			var select = selects[i];
			if(itemtypepattern.test(select.name))
				sortList(select,2);
			else if(itemsetpattern.test(select.name))
				sortList(select,2);
		}
	}
	try {
		filterMain();
		reorderMain();
    } catch (e) {
        alert("Main(): " + e);
    }
})()
var $hilighted,
	$hilightedMenuItem,
	optionDictionary = {},
	names = [],
	buildApiOffline,
	initOffline,
	offline = {},
	API = {},
	buildPage;

function loadScript(url, callback) {
	//http://www.nczonline.net/blog/2009/07/28/the-best-way-to-load-external-javascript/
	var script = document.createElement("script");
	script.type = "text/javascript";
	if (script.readyState){  //IE
		script.onreadystatechange = function(){
			if (script.readyState == "loaded" ||
					script.readyState == "complete"){
				script.onreadystatechange = null;
				callback();
			}
		};
	} else {  //Others
		script.onload = function() {
			callback();
		};
	}

	script.src = url;
	document.getElementsByTagName("head")[0].appendChild(script);
}

function toDot (id){
	return id.replace(/[-]+/g,'.');
};

function escapeHTML(html) {
	if (typeof html === 'string') {
		html = html
			.replace('\u25CF', '\\u25CF')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');
	}
	return html;
}

function escapeSelector (name) {
	return name.replace('<', '\\<').replace('>', '\\>');
}

function activateInternalLinks($parent) {
	$('a[href^="#"]', $parent).each(function (i, anchor) {
		$(anchor).click(function () {
			gotoSection(anchor.href.split('#')[1], true);
			return false;
		});
	});
}


/**
 * Highligth a specific option by coloring it in the menu view and section view
 */
function hilight (id) {
	var linkId, $el, $detailsWrap = $('#details-wrap');

	$el = $('div.member#' + escapeSelector(id));

	// clear old
	if ($hilighted) {
		$hilighted.removeClass('hilighted');
	}
	if ($hilightedMenuItem) {
		$hilightedMenuItem.removeClass('hilighted');
	}

	if ($el.length === 0) {
		$detailsWrap.scrollTop(0);
	} else {
		// hilight new
		$hilighted = $el;
		$hilighted.addClass('hilighted');
		$detailsWrap.scrollTop($hilighted.offset().top + $detailsWrap.scrollTop() - 160);
	}
	linkId = id.replace(/[^a-z0-9<>\\]+/gi,'.');

	$hilightedMenuItem = $('a[href="#'+ linkId +'"]').not('.plus');
	$hilightedMenuItem.addClass('hilighted');

}

/**
 * Expand and load children when necessary of current level
 */
function toggleExpand($elem, callback) {
	var $_menu = $elem.find('div[id$="-menu"]').first(),
		_id = $_menu.attr('id').replace("-menu",""),
		displayChildrenCallback = function () {

			$('.dots', $elem).removeClass('loading');
			$elem.removeClass("collapsed");
			$elem.addClass("expanded");
			$_menu.slideDown();
			// show relevant section

			if (/[A-Z]/.test(_id[0])) {
				_id = 'object-' + _id;
			}
			toggleSection(_id);

			if (callback) {
				callback();
			}

		};


	if ($elem.hasClass('collapsed')) {

		/* if not loaded, load children, standard we have three children */
		if ($_menu.children().size() == 1) {
			$('.dots', $elem).addClass('loading');
			loadChildren(_id, false, displayChildrenCallback);

		} else {
			displayChildrenCallback();
		}
	} else {
		// hide children
		$_menu.slideUp('normal',function(){
			$elem.removeClass("expanded");
			$elem.addClass("collapsed");
		});
	}
};

function toggleSection(sectionId) {
	$section = $("#details > div.section:visible");

	// hide current section
	if($section){
		$section.hide();
	}
	if (/[^\\]</.test(sectionId)) {
		sectionId = sectionId.replace('<', '\\<').replace('>', '\\>');
	}
	$('#details > div.section#' + sectionId).show();
}


function addSectionOption(val){
	$section = $('<div class="section" id="' + val.name + '" style="display:none;"></div>').appendTo('#details');
	$('<h1>' + val.fullname.replace('<', '&lt;').replace('>', '&gt;') + '</h1>'
	+ (val.description ? '<div class="section-description">' + val.description + '</div>': '')
	+ (val.demo ? '<div class="demo"><h4>Try it:</h4> ' + val.demo + '</div>': '' )).appendTo($section);

	activateInternalLinks($section);
	$(document).triggerHandler({ type:"xtra.btn.section.event",id: optionDictionary[val.fullname], table: 'option' });
}

function addSectionObject(val){
	$section = $('<div class="section" id="object-' + val.name + '" style="display:none;"></div>').appendTo('#details');
	$('<h1>' + val.title + '</h1>').appendTo($section);
	$('<div class="section-description">' + val.description + '</div>').appendTo($section);

	activateInternalLinks($section);
	$(document).triggerHandler({ type:"xtra.btn.section.event",id: 'object-'+ val.name, table: 'object'});
}

function markupReturnType(s) {
	s = s.replace(/[<>]/g, function (a) {
		return {
			'<': '&lt;',
			'>': '&gt;'
		}[a];
	});
	s = s.replace(/(Axis|Chart|Element|Highcharts|Point|Renderer|Series)/g, '<a href="#$1">$1</a>');
	return s;
}

function loadOptionMemberInSection(obj, isParent){
	//add member to section in div#details
	var $_section = $('div#' + obj.parent.replace('<', '\\<').replace('>', '\\>') + '.section'),
		$_inheritedLink,
		$memberDiv,
		contextClass = obj.description && obj.description.indexOf('<p>') > -1 ? '' : ' context';

	$memberDiv = $('<div class="member" id="' + obj.name + '"><span class="title">' + obj.title + '</span>'
			+ (obj.returnType ? '<span class="returnType">: ' + markupReturnType(obj.returnType) + '</span>' : '')
			+ (obj.deprecated ? '<div class="deprecated"><p>Deprecated</p></div>' : '' )
			+ (obj.since ? '<div class="since">Since ' + obj.since + '</div>' : '' )
			+ (obj.description ? '<div class="description">' + obj.description
					+ (obj.defaults ? ' Defaults to <code>' + escapeHTML(obj.defaults) + '</code>.'  : '')
					+ '</div>' : '')
			+ (obj.context ? '<div class="description' + contextClass + '">The <code>this</code> keyword refers to the '+ markupReturnType(obj.context) +' object.</div>' : '')
			+ (obj.demo ? '<div class="demo"><h4>Try it:</h4> ' + obj.demo + '</div>': '' )
			+ (obj.seeAlso ? '<div class="seeAlso">See also: ' + obj.seeAlso + '</div>': '' )
			+ '</div>').appendTo($_section);

	activateInternalLinks($memberDiv);

	if (isParent) {
		$('div#' + escapeSelector(obj.name) + '.member span.title').html(function() {
			var title = $.trim($(this).text());
			return $('<a href="#' + obj.fullname + '">' + title + '</a>').click(function(){
				gotoSection(obj.fullname, true);
			});
		});
	}
}

function loadObjectMemberInSection(obj) {
	$memberDiv = $('<div class="member" id="' + obj.name + '">'
			+ '<span class="title">' + obj.title + '</span> '
			+ (obj.params ? '<span class="parameters">' + obj.params + '</span>' : '')
			+ (obj.since ? '<div class="since">Since ' + obj.since + '</div>' : '' )
			+ (obj.deprecated ? '<div class="deprecated"><p>Deprecated</p></div>' : '' )
			+ '<div class="description"><p>' + obj.description +  '</p>'
			+ (obj.paramsDescription ? '<h4>Parameters</h4><ul id="paramdesc"><li>' +
					obj.paramsDescription.replace(/\|\|/g,'</li><li>') + '</li></ul>' : '')
			+ (obj.returnType ? '<h4>Returns</h4><ul id="returns"><li>' + markupReturnType(obj.returnType) + '</li></ul>' : '')
			+ '</div>'
			+ (obj.demo ? '<div class="demo"><h4>Try it:</h4> ' + obj.demo + '</div>': '' )
			+ '</div>').appendTo('div#object-' + obj.parent + '.section');

	activateInternalLinks($memberDiv);
}

function loadChildren(name, silent, callback) {

	var isObject = /[A-Z]/.test(name[0]),
		url = isObject ?
			'object/'+ PRODUCTNAME + '-obj/child/' + name :
			'option/'+ PRODUCTNAME + '/child/' + name;

	$.ajax({
		type: "GET",
		url: url,
		dataType: "json",
		error: function () {
			var $menu;
			$menu = $('div#' + escapeSelector(name) + '-menu');
			$('.dots', $menu.parent()).removeClass('loading').addClass('error').html('Error');
		},
		success: function (data) {
			var display = 'block',
			display, $menu, $menuItem;

			if (silent){
				display = 'none';
			}

			name = name.replace('<', '\\<').replace('>', '\\>');
			$menu = $('div#' + name + '-menu');


			$.each(data, function (key, val) {
				var $div = $('<div></div>').appendTo($menu), $plus, $menuLink, parts,
				tie, dottedName, internalName,
				name,
				title,
				defaults,
				cls;

				/*if (val.type === 'method') {
					name = val.name.replace('--', '.') + '()';
				} else if (val.type === 'property') {
					name = val.name.replace('--', '.');
				} else {
					name = val.fullname;
				}*/
				name = val.fullname;

				if (val.isParent) {
					var preBracket = '{',
						postBracket = '}';

					if (val.returnType && val.returnType.indexOf('Array') === 0 ) {
						preBracket = '[{';
						postBracket = '}]';
					}



					$menuItem = $('<div class="menuitem collapsed"></div>');
					$menuLink = $('<a href="#' + name + '">' + val.title + '</a>').appendTo($menuItem);

					$menuLink.click(function(){
						gotoSection(val.fullname, true);
					});
					$plus = $('<a href="#' + name + '" class="plus"></a>').appendTo($menuItem);
					$plus.click(function () {
						toggleExpand($plus.parent());
					});
					$menuItem.append(':&nbsp;'+ preBracket +'<span class="dots"><span>…</span></span>');
					// add empty submenu
					$subMenu = $('<div id="' + val.name + '-menu" style="display:none"><div>').appendTo($menuItem);
					$menuItem.append(postBracket);
					$menuItem.appendTo($menu);
					addSectionOption(val);
				} else {
					if (val.type === 'method') {
						title = val.title + '()';
					} else {
						title = val.title;
					}

					$menuLink = $('<a href="#' + name + '">' + title + '</a>').appendTo($div);
					$menuLink.click(function() {
						gotoSection(name, true);
					});
					if (val.type === 'method') {
						defaults = '[function]';
					} else if (val.type === 'property') {
						defaults = '[' + val.returnType + ']';
					} else if (val.defaults === 'null' || val.defaults === 'undefined' || val.defaults === '' || val.defaults === undefined) {
						defaults = val.defaults;
					} else if (val.returnType === 'String' || val.returnType === 'Color') {
						defaults = '"' + val.defaults + '"';

					} else {
						defaults = val.defaults;
					}

					if (val.returnType) {
						cls = val.returnType.toLowerCase();
					} else {
						cls = '';
						console.warn('Missing returnType for ' + val.fullname);
					}
						

					$('<span class="value value-' + cls + '">: ' + escapeHTML(defaults) + '</span>').appendTo($div);
				}
				if (isObject) {
					loadObjectMemberInSection(val);
				} else {
					loadOptionMemberInSection(val, val.isParent);
				}
			});

			$(document).triggerHandler({
				type:"xtra.btn.member.event",
				id: isObject ? 'object-' + name : name,
				table: isObject ? 'object' : 'option'
			});

			if (callback) {
				callback();
			}
		}
	});
};

function loadObjectMembers(name){
	$.ajax({
		type: "GET",
		url: 'object/'+ PRODUCTNAME + '-obj/child/' + name,
		async: false,
		dataType: "json",
		success: function (data) {
			$.each(data, function (key, val) {
				loadObjectMemberInSection(val);
			});
		}
	});
	$(document).triggerHandler({ type:"xtra.btn.member.event", id: 'object-' + name,table:'object'});
};

function gotoSection(anchor, hilighted) {

	var name, levels, member, isObjectArr, isObject, parts, $_parent, $_parentparent, $_menu,
		sectionId, parent,
		i,
		callbackStack = [];

	// is it an option-section or an object-section?
	parts = anchor.split("-");

	// Handle typed parent item, like series<line>
	name = anchor.split('.');
	if (name.length > 1) {
		name[name.length - 1] = '-' + name[name.length - 1];
	}
	name = name.join('-');

	levels = name.split(/[-]{1,2}/);

	isObject = (parts.length > 1 && parts[0] == 'object' || /[A-Z]/.test(name[0]));

	// Asyncronously expand parent elements of selected item
	$.each(levels, function(i) {
		callbackStack.push(function () {
			var proceed = true,
				level,
				$_menu,
				$_parent;

			if (levels[i]) {
				level = levels.slice(0, i + 1).join('-');

				if (level.indexOf('<') > -1) {
					$_parentparent = $('#' + level.split('<')[0] + '-menu').parent();
					level = escapeSelector(level);
				}

				$_menu = $('#' + level + '-menu');
				$_parent = $_menu.parent();

				if ($_menu && $_parent.hasClass('collapsed')) {

					if ($_parentparent && $_parentparent.hasClass('collapsed')) {
						toggleExpand($_parentparent);
					}

					// Do the toggle, and pass the next level as the callback argument
					toggleExpand($_parent, callbackStack[i + 1]);
					proceed = false;

				}
			}

			// For the last path item, show the section etc
			if (/[A-Z]/.test(level[0])) {
				level = 'object-' + level;
			}
			if ($('#details > div.section#' + level).length) {
				toggleSection(level);

				// empty search
				$("#search").val("");
				window.location.hash = anchor;
			}

			if (proceed && callbackStack[i + 1]) {
				callbackStack[i + 1]();
			}
		});
	});

	// Hilighting is the last operation in the async stack
	if (hilighted) {
		callbackStack.push(function () {
			hilight(name);
		});
	}

	// Start the recursive iteration
	callbackStack[0]();



}
/*
function addToSelectBox(key, val, type) {

	var $menuItem = $('<div class="menuitem collapsed"></div>').appendTo('#' + type + 's'),
		splut = val.fullname.split('<'),
		commonName = splut[0],
		templateName = splut[1].split('>')[0],
		$menuLink = $('#' + commonName + '-menulink'),
		$selectbox = $('#' + commonName + '-selectbox');

	// The first time we encounter the series, generate the menu item for it.
	if ($menuLink.length === 0) {
		$menuLink = $('<a href="#' + commonName + '" id="' + commonName + '-menulink">' + commonName + '</a>')
			.appendTo($menuItem);

		$menuItem.append(': { type: ');

		$selectbox = $('<select id="'+ commonName +'-selectbox">')
			.bind('change', function () {
				console.log(this.value);
			})
			.appendTo($menuItem);

		$menuItem.append(' }');

	}

	$selectbox.append('<option>' + templateName + '</option>')
		.attr({
			name: templateName
		});
}
*/
/**
 * Add the first level menu items on page load
 */
function addFirstLevelMenuItem(key, val, type) {


	var $menuItem = $('<div class="menuitem collapsed"></div>').appendTo('#' + type + 's'),
		$plus, anchor, $menu, levels, level, member, $menuLink,
		sectionId = val.fullname || val.name,
		title = escapeHTML(val.title),
		mainSection,
		name = val.name,
		recurseToType = false,
		menuItemPrefix = '';
		prefix = ': {',
		suffix = '}';

	if (val.returnType && val.returnType.indexOf('Array') === 0) {
		if (val.returnType === 'Array<Object>') {
			prefix = ': [{';
			suffix = '}]';
		} else {
			prefix = ': [';
			suffix = ']';
		}		
	}
	
	// Global options
	if ($.inArray(val.name, ['global', 'lang']) !== -1) {
		$menuItem = $('<div class="menuitem collapsed"></div>').appendTo('#global-options');
	}


	// Handle the series<line> syntax
	if (sectionId.indexOf('<') > -1) {
		mainSection = sectionId.split('<')[0];

		// The first time we encounter a menu item on the syntax series<line>, add the series menu item
		if ($('#' + mainSection + '-menu').length === 0) {
			sectionId = title = name = mainSection;
			prefix = ': [';
			suffix = ']';
			recurseToType = true; // run this method again, but now for the { type: "line" } menu item
		} else {
			$menuItem.appendTo($('#' + mainSection + '-menu'));
			menuItemPrefix = '{<br class="typed"/>';
			title = '<span class="typed">type: "' + sectionId.split('<')[1].split('>')[0] + '"</span>';
			prefix = ', ';
		}


	}

	if (menuItemPrefix) {
		$menuItem.append(menuItemPrefix);
	}

	$menuLink = $('<a href="#' + sectionId + '">' + title + '</a>')
		.appendTo($menuItem)
		.click(function(){
			gotoSection(sectionId, true);
			return false;
		});

	if (val.isParent) {
		$plus = $('<a href="#' + sectionId + '" class="plus"></a>')
			.appendTo($menuItem)
			.click(function () {
				toggleExpand($plus.parent());
			});
	}

	$menuItem.append(prefix);

	$('<span class="dots"><span>…</span></span>').appendTo($menuItem);

	if(val.isParent) {
		$subMenu = $('<div id="' + name + '-menu" style="display:none"><div>').appendTo($menuItem);
	}
	
	$menuItem.append(suffix);


	// create sections in div#details
	if (type === 'option') {
		addSectionOption(val);
	} else {
		addSectionObject(val);
	}

	if (recurseToType) {
		addFirstLevelMenuItem.apply(null, arguments);
	}
}

prepareOffline = function(callback) {

	offline = {highcharts: {}, highstock: {}, highmaps: {}};

	// now we have the data loaded we rewrite $.ajax for offline use
	$.ajax = function(obj) {
		var result,
			type,
			splitted;

		if (obj.url === PRODUCTNAME + '/names') {
			result = API[PRODUCTNAME].names;
		}

		var type = obj.url.split('/');		

		if (obj.url === 'option/'+ PRODUCTNAME + '/main') {
			result = API[PRODUCTNAME].main.option;
		}

		if (obj.url === 'object/'+ PRODUCTNAME + '-obj/main') {
			result = API[PRODUCTNAME].main.object;
		}

		splitted = obj.url.split('object/' + PRODUCTNAME + '-obj/child/');
		if (splitted.length > 1) {
			result = API[PRODUCTNAME].object[splitted[1]].children;
		}
		splitted = obj.url.split('option/' + PRODUCTNAME + '/child/');
		if (splitted.length > 1) {
			result = API[PRODUCTNAME].option[splitted[1]].children;
		}
		
		// result to handler
		obj.success(result);
	};

	callback();
}

// build dictionary for offline use
buildApiOffline = function(data, callback) {

	var option,		
		main,
		names,
		type,
		i = 0;

	API[PRODUCTNAME] = { option: [], object: [], main: {}, names: [] };
		
	names = API[PRODUCTNAME].names;

	function fillWithType(type) {
		var idx,
			slot = API[PRODUCTNAME][type],
			main = API[PRODUCTNAME].main[type] = [];
			name,
			parent;
		
		// Loop over options in dump file
		for (idx = 0; idx < data[type].length; idx++) {
			option = data[type][idx];
			name = option.name;
			names.push(name);

			if (option.isParent) {
		
				// Store main options separately
				if (!/-/.test(name)) {	  
					main.push(option);
				}
		
				if (slot[name] == undefined) {
					slot[name] = {details: option, children: []};
				} else {
					/* In case the parent option was already 
					 * deducted from a child option 
					 */            	
					slot[name].details = option;
				}            
			}

			// we have a child!
			if (slot.hasOwnProperty(option.parent)) {
				slot[option.parent].children.push(option);
			} else {
				slot[option.parent] = {details: null, children: [option]};
			}
		}	
	}

	while(i < 2) {
		type = ['option', 'object'][i];
		fillWithType(type);
		i++
	}

	callback();

};

buildPage = function() {

		// autocomplete
		$.ajax({
			type: "GET",
			url: PRODUCTNAME + '/names',
			async: false,
			dataType: "json",
			success: function (data) {
				$.each(data, function (key, val) {
					var dotted = toDot(val);
					names.push(dotted);
					optionDictionary[dotted] = val;
				});

				$("#search" ).autocomplete({
					source: names,
					autoFocus: true,
					minLength: 2,
					select: function( event, ui ) {
							gotoSection(ui.item.value, true);
					},
					position: {
						my: 'left top',
						of: '#search-wrap'
					}
				});
			}
		});

		// load main options and build folded menu tree
		$.ajax({
			type: "GET",
			url: 'option/' + PRODUCTNAME + '/main',
			async: false,
			dataType: "json",
			success: function (data) {
				$.each(data, function (key, val) {
					addFirstLevelMenuItem(key, val, 'option');
				});
			}
		});

		// load objects of product
		$.ajax({
			type: "GET",
			url: 'object/' + PRODUCTNAME + '-obj/main',
			async: false,
			dataType: "json",

			success: function (data) {

				$.each(data, function (key, val) {
					addFirstLevelMenuItem(key, val, 'object');
				});
			}
		});

		 // check url for anchor, remove also '()' from old links for object.method().
		 anchor = window.location.hash.replace('#', '').replace('()','');
		 if (anchor) {
			gotoSection(anchor, true);
		 }

		if (/\?object_not_found=true/.test(window.location.search)) {
				dottedName = window.location.hash.split('#').pop();
				internalName = optionDictionary[dottedName];
				$('div#' + internalName).append('<div class="error">The object/option wasn\'t found in the database, maybe iẗ́\'s inherited??</div>');
		}

		 // focus search
		 $("#search")[0].focus();
	}

// Startup
$(document).ready( function () {
	
	if (runDB) {
		buildPage();		
	} else {
		// prepare dump object
		prepareOffline(function () {
			// load offline data
			loadScript('./js/' + PRODUCTNAME + '.json', function() { 
				buildApiOffline(offline[PRODUCTNAME], buildPage);
			});
		});
		// hide elements that don't make sence in offline mode
		$('.hidden-offline').hide();
	};

	// convert hash from redirected dash syntax to new dot syntax
	if (/-/.test(location.hash)) {
		location.hash = location.hash.replace(/(--|-)/g, '.');
	}

	// Add scrollanimation to button
	$("a[href='#top']").click(function() {
		$("html, body").animate({ scrollTop: 0 }, "slow");
		return false;
	});

	$(window).on('scroll', function() {
		button = $("#scrollTop");
		if (!$("#top").isOnScreen()) {
			if (button.css('display') == 'none') {
				button.fadeIn("slow");
			}
		} else {
			if (button.css('display') == 'block') {
				button.fadeOut("slow");
			} 
		}
	});

	$.fn.isOnScreen = function(){
		var win = $(window),
			viewport = {
				top : win.scrollTop(),
				left : win.scrollLeft()
			};
		
		viewport.right = viewport.left + win.width();
		viewport.bottom = viewport.top + win.height();
		
		var bounds = this.offset();
		bounds.right = bounds.left + this.outerWidth();
		bounds.bottom = bounds.top + this.outerHeight();
		
		return (!(viewport.right < bounds.left || viewport.left > bounds.right || viewport.bottom < bounds.top || viewport.top > bounds.bottom));
		
	};

	function updateHeight() {
		if (jQuery(window).width() >= 768) {
			// Disable 
			var padding,
			height = $(window).height() - $('#top').height() - $('#footer').height();
			$("#wrapper").height(height);
			padding = $("#wrapper .container").innerHeight() - $("#wrapper .container").height();
			height = $("#wrapper").height() - padding;
			$("#wrapper-inner").height(height);
			$("#nav-wrap").height(height);
			$("#details-wrap").height(height);
		} else {
			// no height defined on the element for mobile devices
			$('#nav-wrap').removeAttr('style');
		}
	};      
	
	updateHeight();

	$(window).resize(updateHeight);

	// Make the Highcharts/Highstock links dynamic
	$('#highstock-link, #highcharts-link').click(function () {
		this.href += location.hash;
	});

	// Login shortcut (hot corner)
	$("<div>")
		.css({
			position: 'absolute',
			display: 'block',
			width: '10px',
			height: '10px',
			right: 0,
			cursor: 'pointer'
		})
		.click(function () {
				$('<iframe src="auth/login">').dialog({
					height: 300
				});
		})
		.prependTo('#top .container');
	
});




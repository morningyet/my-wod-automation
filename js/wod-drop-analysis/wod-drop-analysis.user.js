// ==UserScript==
// @name         WoD 掉落分析
// @icon         http://info.world-of-dungeons.org/wod/css/WOD.gif
// @namespace    1iuh
// @author       1iuh <liuhsmail@gmail.com>
// @match        http*://delta.world-of-dungeons.org/wod/spiel//dungeon/report.php*
// @match        http*://delta.world-of-dungeons.org/wod/spiel/dungeon/report.php*
// @require      https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js
// @require      https://cdn.jsdelivr.net/npm/axios@0.21.1/dist/axios.min.js
// @require      https://cdn.jsdelivr.net/npm/axios-userscript-adapter@0.1.4/dist/axiosGmxhrAdapter.min.js
// @grant        GM.xmlHttpRequest
// @connect      www.wodgroup.top
// @connect      christophero.xyz
// @modifier     Christophero
// @version      2023.03.24.1
// @updateURL    https://raw.githubusercontent.com/morningyet/my-wod-automation/master/js/wod-drop-analysis/wod-drop-analysis.user.js
// @downloadURL  https://raw.githubusercontent.com/morningyet/my-wod-automation/master/js/wod-drop-analysis/wod-drop-analysis.user.js
// @run-at       document-end
// ==/UserScript==

/******/ (function () {
  // webpackBootstrap
  /******/ var __webpack_modules__ = {
    /***/ "./node_modules/nanobar/nanobar.js": /***/ function (module) {
      /* http://nanobar.micronube.com/  ||  https://github.com/jacoborus/nanobar/    MIT LICENSE */
      (function (root) {
        ("use strict"); // container styles

        var css =
          ".nanobar{width:100%;height:4px;z-index:9999;top:0}.bar{width:0;height:100%;transition:height .3s;background:#000} "; // add required css in head div

        function addCss() {
          var s = document.getElementById("nanobarcss"); // check whether style tag is already inserted

          if (s === null) {
            s = document.createElement("style");
            s.type = "text/css";
            s.id = "nanobarcss";
            document.head.insertBefore(s, document.head.firstChild); // the world

            if (!s.styleSheet)
              return s.appendChild(document.createTextNode(css)); // IE

            s.styleSheet.cssText = css;
          }
        }

        function addClass(el, cls) {
          if (el.classList) el.classList.add(cls);
          else el.className += " " + cls;
        } // create a progress bar
        // this will be destroyed after reaching 100% progress

        function createBar(rm) {
          // create progress element
          var el = document.createElement("div"),
            width = 0,
            here = 0,
            on = 0,
            bar = {
              el: el,
              go: go,
            };
          addClass(el, "bar"); // animation loop

          function move() {
            var dist = width - here;

            if (dist < 0.1 && dist > -0.1) {
              place(here);
              on = 0;

              if (width === 100) {
                el.style.height = 0;
                setTimeout(function () {
                  rm(el);
                }, 300);
              }
            } else {
              place(width - dist / 4);
              setTimeout(go, 16);
            }
          } // set bar width

          function place(num) {
            width = num;
            el.style.width = width + "%";
          }

          function go(num) {
            if (num >= 0) {
              here = num;

              if (!on) {
                on = 1;
                move();
              }
            } else if (on) {
              move();
            }
          }

          return bar;
        }

        function Nanobar(opts) {
          opts = opts || {}; // set options

          var el = document.createElement("div"),
            applyGo,
            nanobar = {
              el: el,
              go: function (p) {
                // expand bar
                applyGo(p); // create new bar when progress reaches 100%

                if (p === 100) {
                  init();
                }
              },
            }; // remove element from nanobar container

          function rm(child) {
            el.removeChild(child);
          } // create and insert progress var in nanobar container

          function init() {
            var bar = createBar(rm);
            el.appendChild(bar.el);
            applyGo = bar.go;
          }

          addCss();
          addClass(el, "nanobar");
          if (opts.id) el.id = opts.id;
          if (opts.classname) addClass(el, opts.classname); // insert container

          if (opts.target) {
            // inside a div
            el.style.position = "relative";
            opts.target.insertBefore(el, opts.target.firstChild);
          } else {
            // on top of the page
            el.style.position = "fixed";
            document.getElementsByTagName("body")[0].appendChild(el);
          }

          init();
          return nanobar;
        }

        if (true) {
          // CommonJS
          module.exports = Nanobar;
        } else {
        }
      })(this);

      /***/
    },

    /******/
  };
  /************************************************************************/
  /******/ // The module cache
  /******/ var __webpack_module_cache__ = {};
  /******/
  /******/ // The require function
  /******/ function __webpack_require__(moduleId) {
    /******/ // Check if module is in cache
    /******/ var cachedModule = __webpack_module_cache__[moduleId];
    /******/ if (cachedModule !== undefined) {
      /******/ return cachedModule.exports;
      /******/
    }
    /******/ // Create a new module (and put it into the cache)
    /******/ var module = (__webpack_module_cache__[moduleId] = {
      /******/ // no module.id needed
      /******/ // no module.loaded needed
      /******/ exports: {},
      /******/
    });
    /******/
    /******/ // Execute the module function
    /******/ __webpack_modules__[moduleId].call(
      module.exports,
      module,
      module.exports,
      __webpack_require__
    );
    /******/
    /******/ // Return the exports of the module
    /******/ return module.exports;
    /******/
  }
  /******/
  /************************************************************************/
  /******/ /* webpack/runtime/compat get default export */
  /******/ !(function () {
    /******/ // getDefaultExport function for compatibility with non-harmony modules
    /******/ __webpack_require__.n = function (module) {
      /******/ var getter =
        module && module.__esModule
          ? /******/ function () {
              return module["default"];
            }
          : /******/ function () {
              return module;
            };
      /******/ __webpack_require__.d(getter, { a: getter });
      /******/ return getter;
      /******/
    };
    /******/
  })();
  /******/
  /******/ /* webpack/runtime/define property getters */
  /******/ !(function () {
    /******/ // define getter functions for harmony exports
    /******/ __webpack_require__.d = function (exports, definition) {
      /******/ for (var key in definition) {
        /******/ if (
          __webpack_require__.o(definition, key) &&
          !__webpack_require__.o(exports, key)
        ) {
          /******/ Object.defineProperty(exports, key, {
            enumerable: true,
            get: definition[key],
          });
          /******/
        }
        /******/
      }
      /******/
    };
    /******/
  })();
  /******/
  /******/ /* webpack/runtime/hasOwnProperty shorthand */
  /******/ !(function () {
    /******/ __webpack_require__.o = function (obj, prop) {
      return Object.prototype.hasOwnProperty.call(obj, prop);
    };
    /******/
  })();
  /******/
  /************************************************************************/
  var __webpack_exports__ = {};
  // This entry need to be wrapped in an IIFE because it need to be in strict mode.
  !(function () {
    "use strict"; // CONCATENATED MODULE: external "axios"

    var external_axios_namespaceObject = axios;
    var external_axios_default = /*#__PURE__*/ __webpack_require__.n(
      external_axios_namespaceObject
    ); // CONCATENATED MODULE: external "axiosGmxhrAdapter"
    var external_axiosGmxhrAdapter_namespaceObject = axiosGmxhrAdapter;
    var external_axiosGmxhrAdapter_default =
      /*#__PURE__*/ __webpack_require__.n(
        external_axiosGmxhrAdapter_namespaceObject
      ); // CONCATENATED MODULE: ./src/utils.ts
    function get(url, config) {
      return axios.get(url, Object.assign({ adapter }, config));
    }
    function post(url, data, config) {
      return external_axios_default().post(
        url,
        data,
        Object.assign({ adapter: external_axiosGmxhrAdapter_default() }, config)
      );
    } // CONCATENATED MODULE: ./src/index.ts

    var __awaiter =
      (undefined && undefined.__awaiter) ||
      function (thisArg, _arguments, P, generator) {
        function adopt(value) {
          return value instanceof P
            ? value
            : new P(function (resolve) {
                resolve(value);
              });
        }
        return new (P || (P = Promise))(function (resolve, reject) {
          function fulfilled(value) {
            try {
              step(generator.next(value));
            } catch (e) {
              reject(e);
            }
          }
          function rejected(value) {
            try {
              step(generator["throw"](value));
            } catch (e) {
              reject(e);
            }
          }
          function step(result) {
            result.done
              ? resolve(result.value)
              : adopt(result.value).then(fulfilled, rejected);
          }
          step((generator = generator.apply(thisArg, _arguments || [])).next());
        });
      };

    var Nanobar = __webpack_require__("./node_modules/nanobar/nanobar.js");
    const SPECIAL_ITEMS_KEY = "specialItems";
    const SPECIAL_ITEMS_VERSION = "specialItemsVersion";
    const SPECIAL_ITEMS_SHINE = "specialItemsShine";
    function main() {
      return __awaiter(this, void 0, void 0, function* () {
        var nanobar;
        var max_num = 0;
        var curr_num = 0;
        var temp_div = document.createElement("div");
        var globalUploadUrl = "http://www.wodgroup.top/upload";
        temp_div.innerHTML = "";
        function ReadPage(temp_div) {
          var form_data = $(temp_div).find("form").serialize();
          // 提取时间
          var datetime_string = $(temp_div).find("h2").eq(0).text();
          var datetime = datetime_string.split(" - ")[0];
          var map_name = datetime_string.split(" - ")[1];
          // 提取掉落明细
          var index = 0;
          var content_table = $(temp_div).find(".content_table");
          var drops = [];
          while (index < 12) {
            var charname = content_table.find("h2").eq(index).text();
            if (charname == "") {
              break;
            }
            var sub_table = content_table
              .children("tbody")
              .children("tr")
              .children("td")
              .children("table")
              .eq(index);
            var desc = sub_table
              .children("tbody")
              .children("tr")
              .children("td")
              .eq(2)
              .find("p");
            if (
              desc
                .text()
                .indexOf(
                  "被打昏了，为了将其安全的带回来，只好把其得到的战利品抛弃了"
                ) > 0
            ) {
              index += 1;
              continue;
            }
            var items = sub_table
              .children("tbody")
              .children("tr")
              .children("td")
              .eq(2)
              .find("a");
            for (var it of items) {
              drops.push({ item_name: it.innerHTML, charname: charname });
            }
            index += 1;
          }
          // 组织数据
          var payload = {
            form_data: form_data,
            datetime: datetime,
            map_name: map_name,
            drops: drops,
          };
          return payload;
        }
        function GetPage(report_id, wod_post_id) {
          var XmlHttp = new XMLHttpRequest();
          XmlHttp.onreadystatechange = function () {
            try {
              if (XmlHttp.readyState == 4 && XmlHttp.status == 200) {
                temp_div.innerHTML = XmlHttp.responseText;
                //Stat.nReadPages = nRepPage;
                //Stat.iscurrentPage = false;
                $("#progress_text").text(
                  "正在统计特产:  " +
                    curr_num +
                    "/" +
                    max_num +
                    "，请勿关闭网页。"
                );
                var payload = ReadPage(temp_div);
                post(globalUploadUrl, payload)
                  .then((res) => {
                    showUploadLog({ ok: true, url: globalUploadUrl, payload, res });
                  })
                  .catch((err) => {
                    showUploadLog({ ok: false, url: globalUploadUrl, payload, err });
                  });
                curr_num += 1;
                var process_val = Math.min(
                  100,
                  Math.round((curr_num / max_num) * 100)
                );
                nanobar.go(process_val);
                if (curr_num == max_num) {
                  $("#progress_text").text("");
                }
              }
            } catch (e) {
              alert("XMLHttpRequest.onreadystatechange(): " + e);
            }
          };
          var URL =
            location.protocol +
            "//" +
            location.host +
            "/wod/spiel/dungeon/report.php";
          var param =
            "wod_post_id=" +
            wod_post_id +
            "&report_id[0]=" +
            report_id +
            "&items[0]=获得物品";
          XmlHttp.open("POST", URL, true);
          XmlHttp.setRequestHeader(
            "Content-type",
            "application/x-www-form-urlencoded"
          );
          XmlHttp.send(param);
        }
        function exportAll() {
          if (
            !confirm(
              "从所有战报中统计特产，需要三至五分钟，统计期间请勿关闭网页。"
            )
          ) {
            return;
          }
          if (curr_num != 0 && curr_num != max_num) {
            return;
          }
          var options = {
            target: document.getElementById("progress_bar"),
          };
          nanobar = new Nanobar(options);
          var wod_post_id = $("input[name=wod_post_id]").val();
          max_num = $(".content_table input[type=hidden]").length;
          curr_num = 0;
          $(".content_table input[type=hidden]").each(function () {
            var report_id = $(this).val();
            GetPage(report_id, wod_post_id);
          });
        }
        function exportAllDrops() {
          globalUploadUrl = "http://www.wodgroup.top/upload";
          exportAll();
        }
        function exportAllDropsMyself() {
          globalUploadUrl = "https://christophero.xyz/wod/reportUpload";
          exportAll();
        }

        // 上传日志记录（完整保留，供导出/重放）
        let uploadLogs = [];

        function ensureLogPanel() {
          if ($("#upload_log_panel").length) return;
          $(
            '<div id="upload_log_panel" style="clear:both;margin-top:8px;max-height:480px;overflow:auto;' +
            'border:1px solid #444;background:#111;padding:8px;font-size:12px;">' +
            '  <div style="margin-bottom:6px;">' +
            '    <span id="upload_log_summary" style="color:#0f0;font-weight:bold;"></span>' +
            '    <input type="button" id="export_log_btn" value="导出日志" class="button clickable" style="float:right;">' +
            '    <input type="button" id="replay_log_btn" value="重放日志" class="button clickable" style="float:right;margin-right:5px;">' +
            '  </div>' +
            '  <div id="upload_log_list"></div>' +
            '  <input type="file" id="replay_file_input" accept=".txt" style="display:none;">' +
            '</div>'
          ).insertAfter("#progress_bar");

          $("#export_log_btn").on("click", exportLog);
          $("#replay_log_btn").on("click", function () {
            $("#replay_file_input").trigger("click");
          });
          $("#replay_file_input").on("change", function (e) {
            const file = e.target.files[0];
            if (file) handleReplayFile(file);
            $(this).val("");
          });
        }

        function showUploadLog({ ok, url, payload, res, err }) {
          ensureLogPanel();
          const status = res ? res.status : "网络错误";
          let resData;
          try {
            resData = res ? res.data : (err && err.message) || String(err);
          } catch (e) {
            resData = String(err);
          }

          uploadLogs.push({
            url,
            payload,
            ok,
            status,
            resData,
            ts: new Date().toLocaleString(),
          });

          $("#upload_log_summary").text(
            `上传进度：成功 ${uploadLogs.filter((l) => l.ok).length} / 失败 ${
              uploadLogs.filter((l) => !l.ok).length
            }  （${url}）`
          );

          const dropsHtml = payload.drops
            .map(
              (d) =>
                `<span style="color:#9cf">${d.item_name}</span><span style="color:#666">←${d.charname}</span>`
            )
            .join("、");

          let respText;
          try {
            respText = JSON.stringify(resData, null, 2);
          } catch (e) {
            respText = String(resData);
          }

          const row = $(
            `<details style="margin:4px 0;border-left:3px solid ${ok ? "#0a0" : "#a00"};padding-left:6px;">` +
            `  <summary style="cursor:pointer;color:${ok ? "#0f0" : "#f00"}">` +
            `    #${uploadLogs.length} ${payload.map_name}（${payload.datetime}）掉 ${payload.drops.length} 件 · HTTP ${status} · ${ok ? "成功" : "失败"}` +
            `  </summary>` +
            `  <div style="margin:6px 0 0 8px;">` +
            `    <div><b>入参 drops：</b>${dropsHtml}</div>` +
            `    <div style="color:#999"><b>form_data：</b><span style="word-break:break-all">${payload.form_data}</span></div>` +
            `    <div><b>返回值：</b><pre style="white-space:pre-wrap;color:#9cf;margin:2px 0">${respText}</pre></div>` +
            `  </div>` +
            `</details>`
          );
          $("#upload_log_list").prepend(row);
        }

        function exportLog() {
          if (!uploadLogs.length) {
            alert("暂无上传日志，请先点击「全量统计」或「联盟全量统计」。");
            return;
          }
          const head =
            "# WoD 掉落分析 · 上传日志\n" +
            "# 说明：以 # 开头的为注释行；其余每行一条 JSON（可重放）\n" +
            "# 重放：点击「重放日志」选择本文件，脚本会按每条记录里的 url 重新 POST payload\n\n";
          const jsonLines = uploadLogs.map((l) => JSON.stringify(l)).join("\n");
          const blob = new Blob(["\ufeff" + head + jsonLines], {
            type: "text/plain;charset=utf-8;",
          });
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = "上传日志.txt";
          a.click();
          URL.revokeObjectURL(a.href);
        }

        function handleReplayFile(file) {
          const reader = new FileReader();
          reader.onload = function (e) {
            const lines = String(e.target.result).split("\n");
            let replayed = 0;
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed || trimmed.startsWith("#")) continue;
              try {
                const entry = JSON.parse(trimmed);
                if (!entry || !entry.url || !entry.payload) continue;
                post(entry.url, entry.payload)
                  .then((res) => {
                    showUploadLog({
                      ok: true,
                      url: entry.url,
                      payload: entry.payload,
                      res,
                    });
                  })
                  .catch((err) => {
                    showUploadLog({
                      ok: false,
                      url: entry.url,
                      payload: entry.payload,
                      err,
                    });
                  });
                replayed += 1;
              } catch (parseErr) {
                // 跳过无法解析的行
              }
            }
            if (replayed) {
              alert(`开始重放 ${replayed} 条日志，结果将追加到上方日志区。`);
            } else {
              alert("未从文件中解析到可重放的日志（需为「导出日志」生成的 txt）。");
            }
          };
          reader.readAsText(file, "utf-8");
        }

        function addMarkClass() {
          let style = document.createElement("style");
          style.type = "text/css";
          let cssText =
            // " .shining-item {background: -webkit-linear-gradient(-90deg, #6170ff 0%, #4bdfff 100%);background: linear-gradient(-90deg, #6170ff 0%, #4bdfff 100%);-webkit-background-clip: text;-webkit-text-fill-color: transparent;}";
            " .special {background: -webkit-linear-gradient(left, #3442c5db, #00d2ff) 0 0 no-repeat;-webkit-background-clip: text;-webkit-text-fill-color: rgba(255, 255, 255, 0.3);text-shadow: 4px 3px 5px #1a8ae276;}" +
            " .shining-item {animation: shine 3s infinite;}" +
            " @keyframes shine {0%{text-shadow: none}30%{text-shadow:0 0 1px #fff, 0 0 4px #dfbe10d0, 0 0 8px #dfbe1060}100%{text-shadow: none}} ";
          if (style.styleSheet) {
            style.styleSheet.cssText = cssText;
          } else {
            style.appendChild(document.createTextNode(cssText));
          }
          document.getElementsByTagName("head")[0].appendChild(style);
        }

        function doMark(specialItemsMap, shine) {
          let markedItemMap = {};
          $('.content_table h3:contains("战利品")+table a').each((i, el) => {
            const itemName = $(el).text();
            if (specialItemsMap.hasOwnProperty(itemName)) {
              $(el).addClass("special");
              if (shine) {
                $(el).addClass("shining-item");
              }
              if (markedItemMap.hasOwnProperty(itemName)) {
                markedItemMap[itemName] += 1;
              } else {
                markedItemMap[itemName] = 1;
              }
            }
          });
          let markedItems = Object.keys(markedItemMap);
          let total = Object.values(markedItemMap).reduce((a, b) => a + b, 0);
          if (markedItems.length) {
            let itemTips = Object.entries(markedItemMap)
              .map(([name, cnt]) => {
                if (cnt > 1) {
                  return name + "*" + cnt;
                } else {
                  return name
                }
              })
              .join(", ");
            let warningHtml = `<p><span class='special ${
              shine ? "shining-item" : ""
            }'>发现特殊无唯一性物品${total}件：
            ${itemTips}</span></p>`;
            $(".main_content .gadget_body  h2:first").append(warningHtml);
          }
        }

        function fetchSpecialItems() {
          // 获取特殊物品信息
          fetch("https://christophero.xyz/wod/item/loadDict", {
            method: "POST",
            body: JSON.stringify({ dictTypeList: ["specialItems"] }),
            headers: {
              "Content-Type": "application/json",
            },
          })
            .then((response) => {
              return response.json();
            })
            .then((res) => {
              if (!(res && res.code === 200)) {
                return;
              }
              const $updatedTip = $("<div>特殊物品数据已更新到最新</div>");
              $updatedTip.appendTo($(".main_content h1+p"));
              setTimeout(() => {
                $updatedTip.remove();
                location.reload();
              }, 2000);
              const data = res.data;
              let specialItemsMap = {};
              for (let item of data["specialItems"]) {
                specialItemsMap[item.label] = item.val;
              }
              localStorage.setItem(
                SPECIAL_ITEMS_KEY,
                JSON.stringify(specialItemsMap)
              );
              localStorage.setItem(SPECIAL_ITEMS_VERSION, new Date().getTime());
            });
        }

        function markItems() {
          let specialItemsStr = localStorage.getItem(SPECIAL_ITEMS_KEY);
          let specialItemsVer = localStorage.getItem(SPECIAL_ITEMS_VERSION);
          let shine = localStorage.getItem(SPECIAL_ITEMS_SHINE);
          let specialItemsMap = {};
          let nowTime = new Date().getTime();
          const $changeShineBtn = $(
            '<input type="button" name="shine" value="切换特殊物品闪烁" class="button clickable">'
          );
          const $forceUpdateBtn = $(
            '<input type="button" name="forceUpdate" value="强制更新特殊物品" class="button clickable">'
          );
          const $dropItemsBtn = $(
            '<input type="button" name="toDropItems" value="查看地城掉落" class="button clickable">'
          );
          $changeShineBtn.click(function () {
            let shineArg = localStorage.getItem(SPECIAL_ITEMS_SHINE);
            if (shineArg) {
              $(".special").removeClass("shining-item");
              localStorage.setItem(SPECIAL_ITEMS_SHINE, "");
            } else {
              $(".special").addClass("shining-item");
              localStorage.setItem(SPECIAL_ITEMS_SHINE, "SHINE");
            }
          });
          $forceUpdateBtn.click(function () {
            fetchSpecialItems();
          });
          $dropItemsBtn.click(function (e) {
            const groupId = $('input[name="gruppe_id"]').val();
            const title = $("h1 ~ h2")[0].childNodes[0].textContent;
            const reg =
              /(昨天|今天|\d{4}年\d{2}月\d{2}日) \d{2}:\d{2}\s+\-\s+(.+)/;
            const groups = reg.exec(title);
            if (groups) {
              window.open(
                `https://christophero.xyz/groupDungeon/${encodeURIComponent(
                  groups[2]
                )}?groupId=${groupId}`,
                "_blank"
              );
            } else {
              alert("未找到地城名称");
            }
          });
          $(".main_content h1+p")
            .append($dropItemsBtn)
            .append($changeShineBtn)
            .append($forceUpdateBtn);
          if (
            specialItemsStr &&
            specialItemsVer &&
            nowTime - specialItemsVer < 7 * 24 * 60 * 60 * 1000
          ) {
            specialItemsMap = JSON.parse(specialItemsStr);
            doMark(specialItemsMap, shine);
          } else {
            fetchSpecialItems();
          }
        }
        // 如果是在战报页面，添加按钮
        var form_data = $("form").serialize();
        if (
          window.location.pathname == "/wod/spiel/dungeon/report.php" ||
          $("h1").text() == "战报"
        ) {
          var c_h1 = $(".gadget_body h1");
          const urlParams = new URLSearchParams(form_data);
          var group_id = urlParams.get("gruppe_id");
          c_h1.before(
            '<input type="button" style="float:right" value="全量统计" id="drops_statistics" class="button clickable">'
          );
          c_h1.before(
            '<input type="button" style="float:right;margin-right: 5px;" value="查看统计表" id="goto_drops_table" class="button clickable">'
          );
          c_h1.before(
            '<input type="button" style="float:right;margin-right: 5px;" value="联盟全量统计" id="drops_statistics_myself" class="button clickable">'
          );
          c_h1.before(
            '<input type="button" style="float:right;margin-right: 5px;" value="查看联盟统计表" id="goto_union_drops_table" class="button clickable">'
          );
          c_h1.before(
            '<input type="button" style="float:right;margin-right: 5px;" value="道具一览" id="goto_all_items" class="button clickable">'
          );
          c_h1.before('<span style="float:right"> 特产：</span>');
          c_h1.before(
            '<div width="100%" id="progress_text" style="text-align: center;"></div>'
          );
          c_h1.before('<div width="100%" id="progress_bar"></div>');
          $("#drops_statistics").on("click", exportAllDrops);
          $("#drops_statistics_myself").on("click", exportAllDropsMyself);
          $("#goto_drops_table").on("click", function () {
            window.open(
              "http://www.wodgroup.top/" + group_id + "/drops",
              "_blank"
            );
          });
          $("#goto_union_drops_table").on("click", function () {
            window.open(
              `https://christophero.xyz/groupDungeon?groupId=${group_id}`,
              "_blank"
            );
          });
          $("#goto_all_items").on("click", function () {
            window.open(`https://christophero.xyz/itemList`, "_blank");
          });
          return;
        }
        // 判断是否在掉落页面
        if ($("h1").text().split(":")[0] == "物品纵览") {
          // 上传
          var payload = ReadPage(document.getElementById("page-border"));
          post("http://www.wodgroup.top/upload", payload).then((res) => {
            console.log(res);
          });
          post("https://christophero.xyz/wod/reportUpload", payload).then(
            (res) => {
              console.log(res);
            }
          );
          addMarkClass();
          markItems();
        }
      });
    }
    main().catch((e) => {
      console.log(e);
    });
  })();
  /******/
})();

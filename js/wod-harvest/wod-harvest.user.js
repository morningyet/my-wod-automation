// ==UserScript==
// @name         WoD 自动收菜
// @name:en      WoD Auto Harvest
// @icon         http://info.world-of-dungeons.org/wod/css/WOD.gif
// @namespace    morningyet
// @author       morningyet
// @description  一键收菜：自动清理超载背包、筛选耗材移入团队仓库、筛选镶嵌材料移入宝库、设置地城时间，循环处理所有英雄。支持间隔可设的定时收菜。内置可卖物品清单，可轮询所有英雄自动按NPC价出售。
// @description:en  One-click harvest: clean overloaded backpack, move consumables to group warehouse, socket materials to treasury, reduce dungeon time, loop all heroes. Configurable interval scheduling.
// @match        http*://delta.world-of-dungeons.org/*
// @match        http*://*.world-of-dungeons.org/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @version      0.4.4
// @updateURL    https://gitee.com/Morningyet/my-wod-automation/raw/master/js/wod-harvest/wod-harvest.user.js
// @downloadURL  https://gitee.com/Morningyet/my-wod-automation/raw/master/js/wod-harvest/wod-harvest.user.js
// @run-at       document-end
// @license      MIT
// ==/UserScript==

(function () {
    'use strict';

    // ============================================================
    // 配置（对应 wod_scheduler.py 的常量）
    // ============================================================
    const ITEM_URL_PATH = '/wod/spiel/hero/items.php';
    const DEFAULT_INTERVAL_MIN = 240;   // 默认定时间隔（分钟）
    const EXTRA_WAIT_MS = 2000;         // 页面稳定等待，对应 Python extra_wait=2
    const STEP_GAP_MS = 800;            // 步骤间最小间隔
    const NAV_WAIT_MS = 5000;           // 点击后探测"是否已开始跳转"的窗口（真正的响应可以慢慢来）
    const STUCK_NAV_MS = 10 * 60 * 1000; // 页面加载挂起看门狗：10 分钟未跳转才强制恢复（WoD 有时真的很慢）
    const PAGE_RETRY_MAX = 3;           // 错误页/404 的自动重试次数
    const HEARTBEAT_STALE_MS = 180000;  // 所有权心跳超时（后台标签页定时器被浏览器节流到约 1 次/分钟，不能设太短）
    const NO_PROGRESS_LIMIT = 25;       // 连续无进展上限（防全部导师英雄/持续失败死循环）
    const TASK_TIMEOUT_MS = 6 * 3600 * 1000; // 任务总超时

    // GM 存储键
    const KEY_TASK = 'harvest_task';               // 当前收菜任务状态（步骤/子状态/进度，跨页面续跑）
    const KEY_INTERVAL = 'harvest_interval_min';   // 定时收菜间隔（分钟）
    const KEY_NEXT_RUN = 'harvest_next_run_ts';    // 下次定时执行的时间戳
    const KEY_SCHED_ON = 'harvest_sched_on';       // 定时收菜开关（true=已启动）
    const KEY_OWNER = 'harvest_owner_tab';         // 任务所有权心跳（多标签页互斥，防重复执行）
    const KEY_LOG = 'harvest_log';                 // 面板日志（最近 200 条，跨页面保留）
    const KEY_PANEL_HIDDEN = 'harvest_panel_hidden';      // 面板整体隐藏开关（菜单里恢复）
    const KEY_PANEL_COLLAPSED = 'harvest_panel_collapsed'; // 面板收起/展开状态（—/+ 按钮，跨页面保持）
    const KEY_SELL_TASK = 'harvest_sell_task';     // 出售任务状态（与收菜任务同构，跨页面续跑）
    const SELL_ROUND_GAP_MS = 3000;     // 出售每步之间的等待（对应 Python 版的 3 秒节奏）

    // ============================================================
    // 可卖物品清单（拷贝自 js/sellable-items.js，1192 条 @同步于2026-09-29）
    // 条目按正则解释：普通物品名即精确匹配；正则写法直接写字符串
    // ============================================================
    const SELLABLE_ITEMS = [
  "三棱刺",
  "亚麻布腰布",
  "企鹅全覆式头盔",
  "企鹅板甲手套",
  "企鹅板甲护腿",
  "企鹅板甲衫",
  "企鹅鳞甲护胸",
  "优良企鹅板甲手套",
  "优良企鹅鳞甲护胸",
  "优良力量毒蛇板甲手套",
  "优良力量毒蛇板甲衫",
  "优良力量火蜥蜴板甲靴",
  "优良力量火蜥蜴皮头盔",
  "优良力量火蜥蜴皮甲",
  "优良力量鳞甲护胸",
  "优良嗜血企鹅皮帽",
  "优良带有拉尚印记的李木发卡",
  "优良带有拉尚印记的黑曜石发卡",
  "优良带有查桑印记的李木腰带",
  "优良带有查桑印记的翡翠戒指",
  "优良带有查桑印记的苹果木发卡",
  "优良带有查桑印记的铁木臂章",
  "优良带有查桑印记的黑曜石腰带",
  "优良带有迪莫桑印记的李木戒指",
  "优良带有迪莫桑印记的翡翠臂章",
  "优良带有迪莫桑印记的苹果木耳环",
  "优良带有迪莫桑印记的苹果木项链",
  "优良带有阿克贝斯印记的琥珀发卡",
  "优良带有阿克贝斯印记的琥珀项链",
  "优良带有阿克贝斯印记的铁木臂章",
  "优良带有阿克雷斯印记的李木项链",
  "优良强效抗魔企鹅鳞甲护胸",
  "优良强效抗魔板甲手套",
  "优良强效抗魔毒蛇链甲护额",
  "优良强效抗魔链甲护额",
  "优良强韧毒蛇皮手套",
  "优良强韧皮上衣",
  "优良意志企鹅皮护腿",
  "优良意志企鹅维京头盔",
  "优良意志护胸",
  "优良意志毒蛇皮帽",
  "优良意志毒蛇皮护腿",
  "优良意志火蜥蜴板甲护肩",
  "优良意志火蜥蜴皮手套",
  "优良意志火蜥蜴皮靴",
  "优良感知企鹅全覆式头盔",
  "优良感知毒蛇板甲衫",
  "优良感知毒蛇皮帽",
  "优良感知毒蛇皮手套",
  "优良感知火蜥蜴板甲护腿",
  "优良感知火蜥蜴皮头盔",
  "优良抗魔企鹅板甲护腿",
  "优良抗魔企鹅板甲衫",
  "优良抗魔企鹅皮手套",
  "优良抗魔毒蛇皮甲",
  "优良抗魔毒蛇皮靴",
  "优良抗魔火蜥蜴皮帽",
  "优良抗魔火蜥蜴皮手套",
  "优良抗魔皮护腿",
  "优良抗魔皮靴",
  "优良敏捷企鹅皮帽",
  "优良敏捷毒蛇板甲护肩",
  "优良敏捷毒蛇皮上衣",
  "优良敏捷毒蛇皮帽",
  "优良敏捷毒蛇皮手套",
  "优良敏捷火蜥蜴皮帽",
  "优良智力企鹅皮靴",
  "优良智力企鹅链甲靴",
  "优良智力毒蛇板甲手套",
  "优良智力毒蛇皮靴",
  "优良智力火蜥蜴皮靴",
  "优良智力皮手套",
  "优良智力链甲手套",
  "优良杀戮毒蛇护胸",
  "优良板甲手套",
  "优良板甲护腿",
  "优良板甲衫",
  "优良次级抗魔企鹅皮护腿",
  "优良次级抗魔企鹅鳞甲护胸",
  "优良次级抗魔板甲衫",
  "优良次级抗魔毒蛇板甲手套",
  "优良次级抗魔毒蛇皮靴",
  "优良次级抗魔火蜥蜴板甲手套",
  "优良次级抗魔火蜥蜴板甲护腿",
  "优良次级抗魔火蜥蜴皮手套",
  "优良次级抗魔火蜥蜴皮护腿",
  "优良次级抗魔火蜥蜴皮靴",
  "优良毒蛇板甲手套",
  "优良毒蛇板甲护肩",
  "优良毒蛇板甲衫",
  "优良毒蛇皮手套",
  "优良活力企鹅皮帽",
  "优良活力企鹅皮靴",
  "优良活力板甲手套",
  "优良活力毒蛇板甲衫",
  "优良活力毒蛇皮帽",
  "优良活力毒蛇皮护腿",
  "优良活力火蜥蜴板甲护腿",
  "优良活力火蜥蜴皮手套",
  "优良活力皮手套",
  "优良活力皮护腿",
  "优良火蜥蜴全覆式头盔",
  "优良火蜥蜴板甲手套",
  "优良火蜥蜴板甲护腿",
  "优良火蜥蜴板甲衫",
  "优良火蜥蜴皮靴",
  "优良灵巧企鹅板甲手套",
  "优良灵巧企鹅皮上衣",
  "优良灵巧企鹅链甲护腿",
  "优良灵巧板甲手套",
  "优良灵巧板甲护腿",
  "优良灵巧毒蛇板甲手套",
  "优良灵巧毒蛇皮手套",
  "优良灵巧毒蛇皮护腿",
  "优良灵巧毒蛇皮靴",
  "优良灵巧火蜥蜴皮帽",
  "优良灵巧火蜥蜴皮护腿",
  "优良灵巧鳞甲护胸",
  "优良灵活企鹅皮上衣",
  "优良灵活企鹅皮手套",
  "优良灵活企鹅链甲手套",
  "优良灵活毒蛇板甲靴",
  "优良灵活毒蛇皮护腿",
  "优良灵活毒蛇皮靴",
  "优良灵活火蜥蜴皮靴",
  "优良灵活火蜥蜴链甲靴",
  "优良灵活皮护腿",
  "优良珍珠戒指",
  "优良珍珠王冠",
  "优良珍珠珠宝腰带",
  "优良珍珠耳环",
  "优良珍珠臂章",
  "优良珍珠项链",
  "优良琥珀耳环",
  "优良琥珀项链",
  "优良白金戒指",
  "优良白金王冠",
  "优良白金珠宝腰带",
  "优良白金耳环",
  "优良白金臂章",
  "优良白金项链",
  "优良白银戒指",
  "优良白银王冠",
  "优良白银珠宝腰带",
  "优良白银耳环",
  "优良白银臂章",
  "优良白银项链",
  "优良皮护腿",
  "优良自信头巾",
  "优良自信徽章",
  "优良自信手镯",
  "优良自信护身符",
  "优良药剂师手镯",
  "优良象牙戒指",
  "优良象牙王冠",
  "优良象牙珠宝腰带",
  "优良象牙耳环",
  "优良象牙臂章",
  "优良象牙项链",
  "优良铁木臂章",
  "优良镶嵌小钻石的珍珠戒指",
  "优良镶嵌小钻石的珍珠王冠",
  "优良镶嵌小钻石的珍珠珠宝腰带",
  "优良镶嵌小钻石的珍珠耳环",
  "优良镶嵌小钻石的珍珠项链",
  "优良镶嵌小钻石的白金戒指",
  "优良镶嵌小钻石的白金王冠",
  "优良镶嵌小钻石的白金珠宝腰带",
  "优良镶嵌小钻石的白金耳环",
  "优良镶嵌小钻石的白金臂章",
  "优良镶嵌小钻石的白金项链",
  "优良镶嵌小钻石的白银戒指",
  "优良镶嵌小钻石的白银王冠",
  "优良镶嵌小钻石的白银珠宝腰带",
  "优良镶嵌小钻石的白银耳环",
  "优良镶嵌小钻石的白银臂章",
  "优良镶嵌小钻石的白银项链",
  "优良镶嵌小钻石的象牙戒指",
  "优良镶嵌小钻石的象牙王冠",
  "优良镶嵌小钻石的象牙珠宝腰带",
  "优良镶嵌小钻石的象牙耳环",
  "优良镶嵌小钻石的象牙臂章",
  "优良镶嵌小钻石的象牙项链",
  "优良镶嵌小钻石的青铜戒指",
  "优良镶嵌小钻石的青铜王冠",
  "优良镶嵌小钻石的青铜珠宝腰带",
  "优良镶嵌小钻石的青铜耳环",
  "优良镶嵌小钻石的青铜臂章",
  "优良镶嵌小钻石的青铜项链",
  "优良镶嵌小钻石的黄金戒指",
  "优良镶嵌小钻石的黄金王冠",
  "优良镶嵌小钻石的黄金珠宝腰带",
  "优良镶嵌小钻石的黄金耳环",
  "优良镶嵌小钻石的黄金臂章",
  "优良镶嵌小钻石的黄金项链",
  "优良镶嵌石棉碎片的珍珠王冠",
  "优良镶嵌石棉碎片的珍珠臂章",
  "优良镶嵌石棉碎片的白银戒指",
  "优良镶嵌石棉碎片的青铜项链",
  "优良镶嵌铜片的青铜耳环",
  "优良青铜戒指",
  "优良青铜王冠",
  "优良青铜珠宝腰带",
  "优良青铜耳环",
  "优良青铜臂章",
  "优良青铜项链",
  "优良魅力企鹅皮上衣",
  "优良魅力企鹅皮帽",
  "优良魅力毒蛇板甲手套",
  "优良魅力毒蛇皮帽",
  "优良魅力毒蛇皮靴",
  "优良魅力火蜥蜴皮护腿",
  "优良魅力火蜥蜴皮靴",
  "优良魅力链甲护额",
  "优良魔法师徽章",
  "优良魔法师戒指",
  "优良黄金戒指",
  "优良黄金王冠",
  "优良黄金珠宝腰带",
  "优良黄金耳环",
  "优良黄金臂章",
  "优良黄金项链",
  "全覆式头盔",
  "准星之口径的1255年转轮手枪",
  "准星之速射的''象牙''转轮手枪",
  "割喉三棱刺",
  "割喉波刃短剑",
  "劈颅斧",
  "力量企鹅护胸",
  "力量企鹅板甲护腿",
  "力量全覆式头盔",
  "力量护胸",
  "力量毒蛇环甲衫",
  "力量火蜥蜴板甲手套",
  "力量火蜥蜴板甲护腿",
  "力量鳞甲护胸",
  "加强企鹅板甲手套",
  "加强企鹅板甲护腿",
  "加强企鹅鳞甲护胸",
  "加强全覆式头盔",
  "加强力量企鹅板甲护肩",
  "加强力量毒蛇链甲手套",
  "加强力量毒蛇鳞甲护胸",
  "加强嗜血企鹅皮帽",
  "加强嗜血火蜥蜴皮头盔",
  "加强弩弦之优良钢制盾弩",
  "加强弩弦之寒冰战用十字弓",
  "加强弩弦之寒冰重型弩枪",
  "加强弩弦之猛毒双矢弩",
  "加强弩弦之猛毒战用十字弓",
  "加强弩弦之猛毒钢制盾弩",
  "加强弩弦之蜻蜓十字弓",
  "加强弩弦之轻型双矢弩",
  "加强弩弦之轻型重型弩枪",
  "加强强效抗魔企鹅全覆式头盔",
  "加强强效抗魔板甲手套",
  "加强强效抗魔毒蛇板甲衫",
  "加强强韧板甲衫",
  "加强强韧毒蛇板甲护肩",
  "加强强韧毒蛇皮护腿",
  "加强强韧毒蛇链甲护额",
  "加强强韧火蜥蜴护胸",
  "加强强韧火蜥蜴板甲护肩",
  "加强强韧火蜥蜴环甲衫",
  "加强强韧火蜥蜴鳞甲护胸",
  "加强意志火蜥蜴板甲靴",
  "加强感知企鹅板甲护腿",
  "加强感知企鹅皮帽",
  "加强感知板甲护肩",
  "加强感知毒蛇板甲手套",
  "加强抗魔企鹅板甲手套",
  "加强抗魔板甲手套",
  "加强抗魔毒蛇全覆式头盔",
  "加强抗魔毒蛇板甲衫",
  "加强抗魔火蜥蜴皮手套",
  "加强敏捷板甲手套",
  "加强敏捷毒蛇护胸",
  "加强敏捷火蜥蜴板甲手套",
  "加强敏捷火蜥蜴板甲衫",
  "加强敏捷维京头盔",
  "加强智力企鹅皮护腿",
  "加强智力毒蛇皮护腿",
  "加强智力火蜥蜴皮靴",
  "加强智力火蜥蜴链甲手套",
  "加强智力链甲靴",
  "加强杀戮企鹅全覆式头盔",
  "加强板甲手套",
  "加强次级抗魔企鹅全覆式头盔",
  "加强次级抗魔企鹅板甲护腿",
  "加强次级抗魔全覆式头盔",
  "加强次级抗魔板甲手套",
  "加强次级抗魔火蜥蜴板甲手套",
  "加强次级抗魔火蜥蜴皮手套",
  "加强毒蛇全覆式头盔",
  "加强毒蛇板甲手套",
  "加强毒蛇板甲护腿",
  "加强毒蛇板甲衫",
  "加强毒蛇鳞甲护胸",
  "加强活力企鹅板甲靴",
  "加强活力企鹅皮帽",
  "加强活力板甲手套",
  "加强活力火蜥蜴鳞甲护胸",
  "加强火蜥蜴全覆式头盔",
  "加强火蜥蜴板甲手套",
  "加强火蜥蜴板甲衫",
  "加强灵巧企鹅板甲手套",
  "加强灵巧企鹅皮手套",
  "加强灵巧板甲护肩",
  "加强灵巧毒蛇板甲手套",
  "加强灵巧火蜥蜴板甲护腿",
  "加强灵巧火蜥蜴板甲衫",
  "加强灵巧火蜥蜴皮手套",
  "加强魅力企鹅全覆式头盔",
  "加强魅力企鹅板甲衫",
  "加强魅力企鹅链甲衫",
  "加强魅力毒蛇环甲衫",
  "加强魅力毒蛇皮上衣",
  "加强魅力火蜥蜴皮护腿",
  "加长之口径的1255年转轮手枪",
  "加长之淬火的1255年转轮手枪",
  "加长之精准的1255年转轮手枪",
  "华丽力量锯刃刀",
  "华丽大砍斧",
  "华丽小型木制攻城盾",
  "华丽小型木制盾",
  "华丽小型铁制防御攻城盾",
  "华丽巨型铁制防御大师攻城盾",
  "华丽愤怒地精劈斧",
  "华丽木制防御大师盾",
  "华丽杜萨克弯刀",
  "华丽流星锤",
  "华丽火焰暗精灵剑",
  "华丽火焰杜萨克弯刀",
  "华丽火焰矮人斧",
  "华丽灵巧杜萨克弯刀",
  "华丽灵巧鹤嘴锄",
  "华丽精准东方斧",
  "华丽精准劈颅斧",
  "华丽绝对命中鹤嘴锄",
  "华丽魔法皮制胸甲",
  "华丽鹤嘴锄",
  "卡尔洛克斯·银眉之双矢弩",
  "卡尔洛克斯·银眉之寒冰战用十字弓",
  "卡尔洛克斯·银眉之寒冰蜻蜓十字弓",
  "卡尔洛克斯·银眉之巨型弩",
  "卡尔洛克斯·银眉之战用十字弓",
  "卡尔洛克斯·银眉之烈风双矢弩",
  "卡尔洛克斯·银眉之烈风战用十字弓",
  "卡尔洛克斯·银眉之烈风石棉发射器",
  "卡尔洛克斯·银眉之烈风重型弩枪",
  "卡尔洛克斯·银眉之猛毒巨型弩",
  "卡尔洛克斯·银眉之猛毒蜻蜓十字弓",
  "卡尔洛克斯·银眉之猛毒钢制盾弩",
  "卡尔洛克斯·银眉之轻型双矢弩",
  "卡尔洛克斯·银眉之轻型战用十字弓",
  "卡尔洛克斯·银眉之轻型重型弩枪",
  "卡尔洛克斯·银眉之重型巨型弩",
  "卡尔洛克斯·银眉之重型弩枪",
  "卡尔洛克斯·银眉之重型战用十字弓",
  "卡尔洛克斯·银眉之重型重型弩枪",
  "卡尔洛克斯·银眉之钢制盾弩",
  "双矢弩",
  "嗜血企鹅皮上衣",
  "嗜血企鹅皮帽",
  "嗜血企鹅皮手套",
  "嗜血企鹅皮护腿",
  "嗜血企鹅皮靴",
  "嗜血毒蛇皮护腿",
  "嗜血火蜥蜴皮上衣",
  "嗜血火蜥蜴皮头盔",
  "嗜血火蜥蜴皮帽",
  "大师级格斗之重型双管枪",
  "大砍斧",
  "天火之垂柳长棍",
  "天火之轻型垂柳长棍",
  "完美李木发卡",
  "完美李木戒指",
  "完美珍珠王冠",
  "完美珍珠耳环",
  "完美珍珠臂章",
  "完美珍珠项链",
  "完美琥珀发卡",
  "完美琥珀戒指",
  "完美琥珀耳环",
  "完美琥珀腰带",
  "完美琥珀臂章",
  "完美琥珀项链",
  "完美白金戒指",
  "完美白金王冠",
  "完美白金耳环",
  "完美白银戒指",
  "完美白银珠宝腰带",
  "完美白银耳环",
  "完美白银臂章",
  "完美白银项链",
  "完美翡翠发卡",
  "完美翡翠戒指",
  "完美翡翠臂章",
  "完美翡翠项链",
  "完美苹果木腰带",
  "完美苹果木项链",
  "完美象牙王冠",
  "完美象牙臂章",
  "完美象牙项链",
  "完美铁木项链",
  "完美镶嵌小钻石的珍珠戒指",
  "完美镶嵌小钻石的珍珠王冠",
  "完美镶嵌小钻石的珍珠珠宝腰带",
  "完美镶嵌小钻石的珍珠耳环",
  "完美镶嵌小钻石的珍珠臂章",
  "完美镶嵌小钻石的珍珠项链",
  "完美镶嵌小钻石的白金戒指",
  "完美镶嵌小钻石的白金王冠",
  "完美镶嵌小钻石的白金珠宝腰带",
  "完美镶嵌小钻石的白金耳环",
  "完美镶嵌小钻石的白金臂章",
  "完美镶嵌小钻石的白金项链",
  "完美镶嵌小钻石的白银戒指",
  "完美镶嵌小钻石的白银王冠",
  "完美镶嵌小钻石的白银珠宝腰带",
  "完美镶嵌小钻石的白银耳环",
  "完美镶嵌小钻石的白银臂章",
  "完美镶嵌小钻石的白银项链",
  "完美镶嵌小钻石的象牙戒指",
  "完美镶嵌小钻石的象牙王冠",
  "完美镶嵌小钻石的象牙珠宝腰带",
  "完美镶嵌小钻石的象牙耳环",
  "完美镶嵌小钻石的象牙臂章",
  "完美镶嵌小钻石的象牙项链",
  "完美镶嵌小钻石的青铜戒指",
  "完美镶嵌小钻石的青铜王冠",
  "完美镶嵌小钻石的青铜珠宝腰带",
  "完美镶嵌小钻石的青铜耳环",
  "完美镶嵌小钻石的青铜臂章",
  "完美镶嵌小钻石的青铜项链",
  "完美镶嵌小钻石的黄金戒指",
  "完美镶嵌小钻石的黄金王冠",
  "完美镶嵌小钻石的黄金珠宝腰带",
  "完美镶嵌小钻石的黄金耳环",
  "完美镶嵌小钻石的黄金臂章",
  "完美镶嵌小钻石的黄金项链",
  "完美镶嵌石棉碎片的象牙戒指",
  "完美镶嵌石棉碎片的黄金王冠",
  "完美镶嵌铜片的白金耳环",
  "完美镶嵌铜片的白金项链",
  "完美镶嵌铜片的白银珠宝腰带",
  "完美青铜戒指",
  "完美青铜王冠",
  "完美青铜珠宝腰带",
  "完美青铜耳环",
  "完美青铜臂章",
  "完美青铜项链",
  "完美黄金王冠",
  "完美黄金珠宝腰带",
  "完美黄金耳环",
  "完美黄金臂章",
  "完美黄金项链",
  "完美黑曜石戒指",
  "完美黑曜石耳环",
  "完美黑曜石项链",
  "宽沿帽",
  "小型木制塔盾",
  "小型木制防御圆盾",
  "小型治疗药水",
  "巧夺天工之精致金属折扇",
  "带导线的飞镖",
  "带有拉尚印记的李木发卡",
  "带有拉尚印记的李木戒指",
  "带有拉尚印记的李木耳环",
  "带有拉尚印记的李木腰带",
  "带有拉尚印记的琥珀发卡",
  "带有拉尚印记的琥珀戒指",
  "带有拉尚印记的琥珀耳环",
  "带有拉尚印记的琥珀腰带",
  "带有拉尚印记的琥珀臂章",
  "带有拉尚印记的琥珀项链",
  "带有拉尚印记的翡翠发卡",
  "带有拉尚印记的翡翠戒指",
  "带有拉尚印记的翡翠耳环",
  "带有拉尚印记的翡翠腰带",
  "带有拉尚印记的翡翠项链",
  "带有拉尚印记的苹果木发卡",
  "带有拉尚印记的苹果木戒指",
  "带有拉尚印记的苹果木耳环",
  "带有拉尚印记的苹果木腰带",
  "带有拉尚印记的苹果木臂章",
  "带有拉尚印记的苹果木项链",
  "带有拉尚印记的铁木戒指",
  "带有拉尚印记的铁木耳环",
  "带有拉尚印记的铁木腰带",
  "带有拉尚印记的铁木臂章",
  "带有拉尚印记的铁木项链",
  "带有拉尚印记的黑曜石腰带",
  "带有拉尚印记的黑曜石臂章",
  "带有拉尚印记的黑曜石项链",
  "带有查桑印记的李木发卡",
  "带有查桑印记的李木耳环",
  "带有查桑印记的李木腰带",
  "带有查桑印记的李木臂章",
  "带有查桑印记的李木项链",
  "带有查桑印记的琥珀发卡",
  "带有查桑印记的琥珀戒指",
  "带有查桑印记的琥珀耳环",
  "带有查桑印记的琥珀腰带",
  "带有查桑印记的琥珀臂章",
  "带有查桑印记的琥珀项链",
  "带有查桑印记的翡翠戒指",
  "带有查桑印记的翡翠耳环",
  "带有查桑印记的翡翠腰带",
  "带有查桑印记的翡翠项链",
  "带有查桑印记的苹果木发卡",
  "带有查桑印记的苹果木戒指",
  "带有查桑印记的苹果木耳环",
  "带有查桑印记的苹果木腰带",
  "带有查桑印记的苹果木臂章",
  "带有查桑印记的苹果木项链",
  "带有查桑印记的铁木发卡",
  "带有查桑印记的铁木戒指",
  "带有查桑印记的铁木耳环",
  "带有查桑印记的铁木腰带",
  "带有查桑印记的铁木臂章",
  "带有查桑印记的黑曜石发卡",
  "带有查桑印记的黑曜石戒指",
  "带有查桑印记的黑曜石臂章",
  "带有查桑印记的黑曜石项链",
  "带有迪莫桑印记的李木发卡",
  "带有迪莫桑印记的李木戒指",
  "带有迪莫桑印记的李木耳环",
  "带有迪莫桑印记的李木腰带",
  "带有迪莫桑印记的李木项链",
  "带有迪莫桑印记的琥珀发卡",
  "带有迪莫桑印记的琥珀戒指",
  "带有迪莫桑印记的琥珀耳环",
  "带有迪莫桑印记的琥珀腰带",
  "带有迪莫桑印记的琥珀臂章",
  "带有迪莫桑印记的琥珀项链",
  "带有迪莫桑印记的翡翠发卡",
  "带有迪莫桑印记的翡翠戒指",
  "带有迪莫桑印记的翡翠耳环",
  "带有迪莫桑印记的苹果木发卡",
  "带有迪莫桑印记的苹果木戒指",
  "带有迪莫桑印记的苹果木耳环",
  "带有迪莫桑印记的苹果木腰带",
  "带有迪莫桑印记的苹果木臂章",
  "带有迪莫桑印记的苹果木项链",
  "带有迪莫桑印记的铁木发卡",
  "带有迪莫桑印记的铁木戒指",
  "带有迪莫桑印记的铁木腰带",
  "带有迪莫桑印记的铁木臂章",
  "带有迪莫桑印记的黑曜石发卡",
  "带有迪莫桑印记的黑曜石耳环",
  "带有迪莫桑印记的黑曜石臂章",
  "带有阿克贝斯印记的李木发卡",
  "带有阿克贝斯印记的李木戒指",
  "带有阿克贝斯印记的李木臂章",
  "带有阿克贝斯印记的李木项链",
  "带有阿克贝斯印记的琥珀发卡",
  "带有阿克贝斯印记的琥珀戒指",
  "带有阿克贝斯印记的琥珀耳环",
  "带有阿克贝斯印记的琥珀腰带",
  "带有阿克贝斯印记的琥珀臂章",
  "带有阿克贝斯印记的琥珀项链",
  "带有阿克贝斯印记的翡翠戒指",
  "带有阿克贝斯印记的翡翠耳环",
  "带有阿克贝斯印记的翡翠腰带",
  "带有阿克贝斯印记的翡翠臂章",
  "带有阿克贝斯印记的翡翠项链",
  "带有阿克贝斯印记的苹果木发卡",
  "带有阿克贝斯印记的苹果木戒指",
  "带有阿克贝斯印记的苹果木耳环",
  "带有阿克贝斯印记的苹果木腰带",
  "带有阿克贝斯印记的苹果木臂章",
  "带有阿克贝斯印记的苹果木项链",
  "带有阿克贝斯印记的铁木发卡",
  "带有阿克贝斯印记的铁木戒指",
  "带有阿克贝斯印记的铁木耳环",
  "带有阿克贝斯印记的铁木腰带",
  "带有阿克贝斯印记的铁木项链",
  "带有阿克贝斯印记的黑曜石戒指",
  "带有阿克贝斯印记的黑曜石腰带",
  "带有阿克贝斯印记的黑曜石项链",
  "带有阿克雷斯印记的李木发卡",
  "带有阿克雷斯印记的李木戒指",
  "带有阿克雷斯印记的李木腰带",
  "带有阿克雷斯印记的李木臂章",
  "带有阿克雷斯印记的李木项链",
  "带有阿克雷斯印记的琥珀发卡",
  "带有阿克雷斯印记的琥珀戒指",
  "带有阿克雷斯印记的琥珀耳环",
  "带有阿克雷斯印记的琥珀腰带",
  "带有阿克雷斯印记的琥珀臂章",
  "带有阿克雷斯印记的琥珀项链",
  "带有阿克雷斯印记的翡翠发卡",
  "带有阿克雷斯印记的翡翠戒指",
  "带有阿克雷斯印记的翡翠耳环",
  "带有阿克雷斯印记的翡翠腰带",
  "带有阿克雷斯印记的翡翠臂章",
  "带有阿克雷斯印记的翡翠项链",
  "带有阿克雷斯印记的苹果木发卡",
  "带有阿克雷斯印记的苹果木戒指",
  "带有阿克雷斯印记的苹果木耳环",
  "带有阿克雷斯印记的苹果木腰带",
  "带有阿克雷斯印记的苹果木臂章",
  "带有阿克雷斯印记的苹果木项链",
  "带有阿克雷斯印记的铁木发卡",
  "带有阿克雷斯印记的铁木戒指",
  "带有阿克雷斯印记的铁木耳环",
  "带有阿克雷斯印记的铁木腰带",
  "带有阿克雷斯印记的铁木臂章",
  "带有阿克雷斯印记的铁木项链",
  "带有阿克雷斯印记的黑曜石戒指",
  "带有阿克雷斯印记的黑曜石耳环",
  "带有阿克雷斯印记的黑曜石腰带",
  "带有阿克雷斯印记的黑曜石臂章",
  "异化的边境守卫斧枪",
  "弹仓之口径的1255年转轮手枪",
  "弹仓之淬火的1255年转轮手枪",
  "弹仓之精准的''象牙''转轮手枪",
  "弹仓之速射的1255年转轮手枪",
  "强力劈颅斧",
  "强化枪管之月石长滑膛枪",
  "强化枪管之简易月石喷铅枪",
  "强效抗魔企鹅皮帽",
  "强效抗魔企鹅皮手套",
  "强效抗魔毒蛇皮护腿",
  "强效抗魔毒蛇皮靴",
  "强效抗魔火蜥蜴板甲手套",
  "强效抗魔火蜥蜴链甲手套",
  "强韧企鹅板甲手套",
  "强韧企鹅链甲手套",
  "强韧企鹅链甲靴",
  "强韧板甲手套",
  "强韧毒蛇板甲手套",
  "强韧毒蛇鳞甲护胸",
  "强韧火蜥蜴板甲手套",
  "强韧火蜥蜴板甲护肩",
  "强韧火蜥蜴环甲衫",
  "强韧火蜥蜴皮帽",
  "强韧火蜥蜴链甲手套",
  "强韧火蜥蜴链甲衫",
  "强韧火蜥蜴链甲靴",
  "强韧皮靴",
  "彩色嗜血毒蛇皮帽",
  "彩色强效抗魔企鹅皮护腿",
  "彩色抗魔皮上衣",
  "彩色敏捷企鹅皮手套",
  "彩色敏捷企鹅皮甲",
  "彩色敏捷火蜥蜴皮护腿",
  "彩色次级抗魔企鹅皮帽",
  "彩色次级抗魔企鹅皮甲",
  "彩色次级抗魔毒蛇皮手套",
  "彩色次级抗魔毒蛇皮靴",
  "彩色次级抗魔火蜥蜴皮手套",
  "彩色次级抗魔火蜥蜴皮甲",
  "彩色次级抗魔皮帽",
  "彩色毒蛇皮帽",
  "彩色毒蛇皮甲",
  "彩色火蜥蜴皮靴",
  "彩色魅力企鹅皮甲",
  "意志板甲手套",
  "意志毒蛇鳞甲护胸",
  "意志火蜥蜴板甲手套",
  "意志火蜥蜴板甲护腿",
  "意志火蜥蜴环甲衫",
  "意志链甲护腿",
  "意志链甲衫",
  "感知企鹅环甲衫",
  "感知企鹅皮护腿",
  "感知全覆式头盔",
  "感知板甲手套",
  "感知毒蛇板甲手套",
  "感知毒蛇板甲靴",
  "感知毒蛇环甲衫",
  "感知毒蛇皮靴",
  "感知毒蛇链甲护额",
  "感知火蜥蜴板甲手套",
  "感知火蜥蜴板甲靴",
  "感知火蜥蜴皮上衣",
  "感知火蜥蜴皮靴",
  "战斗大师之海力夫之剑",
  "战神之垂柳魔杖",
  "战神之轻型垂柳长棍",
  "战神之轻型垂柳魔杖",
  "抗魔企鹅板甲手套",
  "抗魔企鹅皮靴",
  "抗魔板甲手套",
  "抗魔毒蛇板甲手套",
  "抗魔毒蛇板甲衫",
  "抗魔火蜥蜴板甲手套",
  "抗魔火蜥蜴板甲护腿",
  "改良之割喉波刃短剑",
  "改良之波刃短剑",
  "改良之砍击者波刃短剑",
  "改良大砍斧",
  "改良杜萨克弯刀",
  "改良流星锤",
  "改良火焰流星锤",
  "改良灵巧杜萨克弯刀",
  "敏捷企鹅板甲手套",
  "敏捷企鹅板甲衫",
  "敏捷企鹅皮上衣",
  "敏捷企鹅皮头盔",
  "敏捷企鹅链甲手套",
  "敏捷企鹅链甲护肩",
  "敏捷企鹅链甲护腿",
  "敏捷企鹅链甲护额",
  "敏捷板甲护肩",
  "敏捷毒蛇板甲手套",
  "敏捷毒蛇皮帽",
  "敏捷毒蛇链甲手套",
  "敏捷毒蛇链甲护腿",
  "敏捷毒蛇链甲衫",
  "敏捷火蜥蜴板甲手套",
  "敏捷火蜥蜴链甲手套",
  "敏捷链甲手套",
  "新人指导手册",
  "普通坚韧东方斧",
  "普通大砍斧",
  "普通布护腿",
  "普通格斗用军刀",
  "普通粗呢大衣",
  "普通精准劈颅斧",
  "智力企鹅全覆式头盔",
  "智力企鹅板甲护腿",
  "智力企鹅板甲衫",
  "智力板甲手套",
  "智力板甲靴",
  "智力毒蛇板甲手套",
  "智力毒蛇板甲衫",
  "智力火蜥蜴板甲手套",
  "智力火蜥蜴皮护腿",
  "月石喷铅枪",
  "月石滑膛枪",
  "木制防御盾",
  "李木项链",
  "板甲手套",
  "板甲护腿",
  "板甲衫",
  "树根制作之优良重型抛石机",
  "次级抗魔企鹅板甲手套",
  "次级抗魔企鹅板甲衫",
  "次级抗魔全覆式头盔",
  "次级抗魔板甲手套",
  "次级抗魔板甲衫",
  "次级抗魔毒蛇板甲手套",
  "次级抗魔毒蛇板甲护腿",
  "次级抗魔毒蛇皮护腿",
  "次级抗魔毒蛇皮靴",
  "次级抗魔毒蛇鳞甲护胸",
  "次级抗魔火蜥蜴板甲手套",
  "次级抗魔火蜥蜴板甲护腿",
  "次级抗魔火蜥蜴板甲衫",
  "正途之重型垂柳六尺棍",
  "正途之重型垂柳坚固手杖",
  "毒蛇全覆式头盔",
  "毒蛇板甲手套",
  "毒蛇板甲护腿",
  "毒蛇板甲衫",
  "毒蛇鳞甲护胸",
  "波刃短剑",
  "活力企鹅板甲手套",
  "活力企鹅皮手套",
  "活力板甲手套",
  "活力板甲护肩",
  "活力毒蛇板甲手套",
  "活力毒蛇板甲衫",
  "活力毒蛇皮护腿",
  "活力火蜥蜴板甲手套",
  "活力火蜥蜴板甲护腿",
  "活力火蜥蜴皮帽",
  "活力火蜥蜴皮手套",
  "活力火蜥蜴皮护腿",
  "活力火蜥蜴鳞甲护胸",
  "活力钢制护胫",
  "活力鳞甲护胸",
  "流星锤",
  "浑然天成之传世纸制折扇",
  "火蜥蜴全覆式头盔",
  "火蜥蜴板甲手套",
  "火蜥蜴板甲护肩",
  "火蜥蜴板甲护腿",
  "火蜥蜴板甲衫",
  "火蜥蜴链甲手套",
  "火蜥蜴链甲靴",
  "火蜥蜴鳞甲护胸",
  "灵巧企鹅全覆式头盔",
  "灵巧企鹅板甲手套",
  "灵巧企鹅链甲护腿",
  "灵巧毒蛇板甲手套",
  "灵巧毒蛇板甲靴",
  "灵巧毒蛇皮头盔",
  "灵巧毒蛇皮护腿",
  "灵巧毒蛇链甲护额",
  "灵巧流星锤",
  "灵巧火蜥蜴板甲手套",
  "灵巧火蜥蜴板甲护腿",
  "灵巧火蜥蜴板甲衫",
  "灵巧火蜥蜴环甲衫",
  "灵巧火蜥蜴皮头盔",
  "灵巧火蜥蜴皮帽",
  "灵巧火蜥蜴链甲护额",
  "灵活企鹅皮手套",
  "灵活企鹅链甲手套",
  "灵活企鹅鳞甲护胸",
  "灵活毒蛇皮靴",
  "灵活毒蛇链甲手套",
  "灵活毒蛇链甲衫",
  "灵活火蜥蜴板甲手套",
  "灵活火蜥蜴链甲护腿",
  "灵活火蜥蜴链甲护额",
  "灵活火蜥蜴链甲衫",
  "灵活环甲衫",
  "烈风重型弩枪",
  "燃烧之口径的1255年转轮手枪",
  "燃烧之精准的1255年转轮手枪",
  "燃烧之速射的1255年转轮手枪",
  "猛毒重型弩枪",
  "珍珠戒指",
  "白色丝绸手套",
  "白金戒指",
  "白金王冠",
  "白金耳环",
  "白金项链",
  "瞄准器之改良月石长滑膛枪",
  "瞄准器之月石喷铅枪",
  "瞄准器之简易矮人喷铅枪",
  "瞄准器之轻型改良月石喷铅枪",
  "瞄准器之重型月石喷铅枪",
  "矮人之优良战用十字弓",
  "矮人之优良钢制盾弩",
  "矮人之双矢弩",
  "矮人之寒冰巨型弩",
  "矮人之寒冰战用十字弓",
  "矮人之寒冰蜻蜓十字弓",
  "矮人之战用十字弓",
  "矮人之烈风巨型弩",
  "矮人之烈风战用十字弓",
  "矮人之烈风蜻蜓十字弓",
  "矮人之猛毒巨型弩",
  "矮人之猛毒战用十字弓",
  "矮人之猛毒重型弩枪",
  "矮人之轻型双矢弩",
  "矮人之轻型巨型弩",
  "矮人之轻型战用十字弓",
  "矮人之轻型蜻蜓十字弓",
  "矮人之重型双矢弩",
  "矮人之重型巨型弩",
  "矮人之重型战用十字弓",
  "矮人之重型蜻蜓十字弓",
  "矮人之重型重型弩枪",
  "矮人之重型钢制盾弩",
  "矮人之钢制盾弩",
  "矮人长滑膛枪",
  "石英之华丽力量大砍斧",
  "石英之华丽流星锤",
  "石英之华丽鹤嘴锄",
  "石英之杜萨克弯刀",
  "石英之流星锤",
  "石英之灵巧流星锤",
  "石英之绝对命中精灵利刃",
  "石英之重型活力钉头锤",
  "石英之重型火焰马刀",
  "石英之重型精灵利刃",
  "石英之重型野蛮人标枪",
  "石英之重型长枪",
  "石英之长枪",
  "石英之长柄镰刀",
  "砍击者三棱刺",
  "砍击者波刃短剑",
  "祝福抗火手镯",
  "祝福抵抗徽章",
  "祝福抵抗护身符",
  "神圣嗜血火蜥蜴皮护腿",
  "神圣强韧企鹅板甲护腿",
  "神圣强韧护胸",
  "神圣强韧毒蛇板甲手套",
  "神圣意志火蜥蜴环甲衫",
  "神圣感知护胸",
  "神圣感知火蜥蜴全覆式头盔",
  "神圣抗魔企鹅皮手套",
  "神圣抗魔毒蛇皮上衣",
  "神圣拉尚祈祷戒指",
  "神圣查桑权杖",
  "神圣查桑祈祷戒指",
  "神圣次级抗魔企鹅皮头盔",
  "神圣次级抗魔企鹅皮护腿",
  "神圣次级抗魔企鹅皮靴",
  "神圣次级抗魔毒蛇板甲护腿",
  "神圣次级抗魔毒蛇皮甲",
  "神圣次级抗魔火蜥蜴皮上衣",
  "神圣次级抗魔火蜥蜴皮手套",
  "神圣次级抗魔火蜥蜴皮甲",
  "神圣次级抗魔皮帽",
  "神圣次级抗魔皮靴",
  "神圣次级抗魔链甲手套",
  "神圣次级抗魔链甲衫",
  "神圣毒蛇板甲护肩",
  "神圣毒蛇鳞甲护胸",
  "神圣活力护胸",
  "神圣活力火蜥蜴全覆式头盔",
  "神圣活力火蜥蜴护胸",
  "神圣火蜥蜴护胸",
  "神圣灵巧毒蛇链甲护腿",
  "神圣阿克贝斯祈祷法杖",
  "神圣阿克雷斯祈祷手镯",
  "神圣阿克雷斯祈祷法杖",
  "简易亚麻布绣花腰布",
  "简易亚麻布腰布",
  "简易小型木制攻城盾",
  "简易小型钢制攻城盾",
  "简易小型钢制防御圆盾",
  "简易小型钢制防御盾",
  "简易小型镍制防御大师圆盾",
  "简易小型镍制防御大师攻城盾",
  "简易巨型钢制防御圆盾",
  "简易月石喷铅枪",
  "简易月石长滑膛枪",
  "简易木制攻城盾",
  "简易狂暴者加固腰布",
  "简易狂暴者腰布",
  "简易白金戒指",
  "简易白金王冠",
  "简易白金项链",
  "简易自信头巾",
  "简易自信徽章",
  "简易自信戒指",
  "简易自信手镯",
  "简易自信护身符",
  "简易钢制护腕",
  "简易镶嵌小钻石的珍珠戒指",
  "简易镶嵌小钻石的珍珠王冠",
  "简易镶嵌小钻石的白金戒指",
  "简易镶嵌小钻石的白金王冠",
  "简易镶嵌小钻石的白金耳环",
  "简易镶嵌小钻石的白金项链",
  "简易镶嵌小钻石的黄金王冠",
  "简易镶嵌铜片的白金戒指",
  "简易镶嵌铜片的白金项链",
  "简易镶嵌铜片的黄金戒指",
  "简易魔法腰布",
  "精准劈颅斧",
  "精准大砍斧",
  "绝对命中长柄镰刀",
  "绳索",
  "绳鞋",
  "翡翠发卡",
  "翡翠戒指",
  "翡翠腰带",
  "自信之野山毛榉特里法克斯木杖",
  "自信之风岑双节棍",
  "自信头巾",
  "自信徽章",
  "自信戒指",
  "自信手镯",
  "自信护身符",
  "致幻烟草果",
  "良好亚麻布绣花腰布",
  "良好亚麻布腰布",
  "英雄企鹅皮手套",
  "英雄企鹅皮护腿",
  "英雄力量企鹅维京头盔",
  "英雄强效抗魔企鹅鳞甲护胸",
  "英雄强效抗魔皮上衣",
  "英雄强韧火蜥蜴皮手套",
  "英雄意志护胸",
  "英雄意志火蜥蜴皮靴",
  "英雄意志链甲护额",
  "英雄感知毒蛇板甲靴",
  "英雄感知火蜥蜴鳞甲护胸",
  "英雄抗魔毒蛇环甲衫",
  "英雄抗魔火蜥蜴皮上衣",
  "英雄抗魔皮护腿",
  "英雄护胸",
  "英雄敏捷毒蛇护胸",
  "英雄敏捷毒蛇板甲手套",
  "英雄次级抗魔企鹅皮头盔",
  "英雄次级抗魔企鹅皮靴",
  "英雄次级抗魔企鹅维京头盔",
  "英雄次级抗魔毒蛇皮靴",
  "英雄次级抗魔火蜥蜴板甲手套",
  "英雄次级抗魔火蜥蜴皮帽",
  "英雄次级抗魔火蜥蜴皮手套",
  "英雄次级抗魔皮上衣",
  "英雄毒蛇皮靴",
  "英雄毒蛇链甲靴",
  "英雄活力企鹅板甲靴",
  "英雄活力毒蛇链甲衫",
  "英雄火蜥蜴皮头盔",
  "英雄火蜥蜴皮帽",
  "英雄火蜥蜴皮靴",
  "英雄火蜥蜴链甲护腿",
  "英雄灵巧火蜥蜴板甲衫",
  "英雄灵活企鹅板甲手套",
  "英雄灵活企鹅皮手套",
  "英雄灵活火蜥蜴全覆式头盔",
  "英雄魅力火蜥蜴皮帽",
  "英雄魅力维京头盔",
  "英雄魅力链甲靴",
  "苹果木耳环",
  "装有魔法毒小刀的精致暗器护腕",
  "贯穿合成弓",
  "贯穿月刃弓",
  "贯穿白蜡木弓",
  "贵族企鹅板甲手套",
  "贵族企鹅皮靴",
  "贵族力量企鹅板甲衫",
  "贵族力量火蜥蜴板甲靴",
  "贵族嗜血企鹅皮帽",
  "贵族强效抗魔企鹅皮靴",
  "贵族强韧板甲护肩",
  "贵族强韧毒蛇全覆式头盔",
  "贵族强韧火蜥蜴皮上衣",
  "贵族感知企鹅皮帽",
  "贵族感知毒蛇链甲靴",
  "贵族感知环甲衫",
  "贵族感知链甲手套",
  "贵族抗魔企鹅板甲护腿",
  "贵族抗魔企鹅皮上衣",
  "贵族抗魔企鹅皮手套",
  "贵族抗魔企鹅皮甲",
  "贵族抗魔毒蛇链甲衫",
  "贵族抗魔火蜥蜴板甲手套",
  "贵族抗魔火蜥蜴皮靴",
  "贵族抗魔火蜥蜴链甲护腿",
  "贵族敏捷企鹅全覆式头盔",
  "贵族敏捷毒蛇链甲护额",
  "贵族敏捷火蜥蜴鳞甲护胸",
  "贵族智力企鹅板甲靴",
  "贵族智力企鹅链甲护额",
  "贵族智力板甲靴",
  "贵族智力毒蛇板甲衫",
  "贵族智力毒蛇环甲衫",
  "贵族智力毒蛇链甲手套",
  "贵族板甲手套",
  "贵族板甲衫",
  "贵族次级抗魔企鹅皮上衣",
  "贵族次级抗魔企鹅皮手套",
  "贵族次级抗魔板甲护肩",
  "贵族次级抗魔板甲护腿",
  "贵族次级抗魔毒蛇全覆式头盔",
  "贵族次级抗魔毒蛇皮帽",
  "贵族次级抗魔火蜥蜴皮手套",
  "贵族次级抗魔皮上衣",
  "贵族次级抗魔皮护腿",
  "贵族次级抗魔皮甲",
  "贵族次级抗魔链甲靴",
  "贵族毒蛇皮头盔",
  "贵族毒蛇链甲护腿",
  "贵族活力企鹅板甲衫",
  "贵族活力毒蛇板甲手套",
  "贵族活力毒蛇皮护腿",
  "贵族活力火蜥蜴皮护腿",
  "贵族活力皮靴",
  "贵族火蜥蜴板甲手套",
  "贵族火蜥蜴板甲护腿",
  "贵族火蜥蜴板甲衫",
  "贵族火蜥蜴皮手套",
  "贵族火蜥蜴皮靴",
  "贵族灵巧板甲手套",
  "贵族灵巧毒蛇鳞甲护胸",
  "贵族灵巧火蜥蜴链甲手套",
  "贵族灵活企鹅板甲衫",
  "贵族灵活企鹅皮帽",
  "贵族灵活企鹅皮护腿",
  "贵族灵活火蜥蜴皮靴",
  "贵族皮头盔",
  "贵族皮护腿",
  "贵族皮靴",
  "贵族维京头盔",
  "贵族魅力企鹅链甲护额",
  "贵族魅力全覆式头盔",
  "贵族魅力火蜥蜴全覆式头盔",
  "轻型亚麻布加固腰布",
  "轻型亚麻布绣花腰布",
  "轻型劈颅斧",
  "轻型加强巴博许护带",
  "轻型双矢弩",
  "轻型小型木制防御大师圆盾",
  "轻型小型木制防御盾",
  "轻型小型铁制防御圆盾",
  "轻型改良月石喷铅枪",
  "轻型木制攻城盾",
  "轻型燧石手枪",
  "轻型石棉发射器",
  "轻型简易月石喷铅枪",
  "轻型简易月石火绳枪",
  "轻型精准劈颅斧",
  "轻型精准月刃弓",
  "轻型重型弩枪",
  "轻型钢制胸甲",
  "轻型铁制攻城盾",
  "轻型魔法皮制胸甲",
  "轻骑士盾",
  "迪莫桑权杖",
  "重型劈颅斧",
  "重型双矢弩",
  "重型复合弓",
  "重型大砍斧",
  "重型弩枪",
  "重型战用十字弓",
  "重型改良月石滑膛枪",
  "重型流星锤",
  "重型火焰白蜡木弓",
  "重型火焰骑射弓",
  "重型灵巧合成弓",
  "重型石棉发射器",
  "重型简易月石喷铅枪",
  "重型简易月石长滑膛枪",
  "重型精准合成弓",
  "重型精准白蜡木弓",
  "重型绝对命中流星锤",
  "重型绝对命中精灵利刃",
  "重型绝对命中鹤嘴锄",
  "重型贯穿白蜡木弓",
  "重型重型弩枪",
  "重型钢制盾弩",
  "钢制护腕",
  "钢制盾弩",
  "钢制胸甲",
  "铁木戒指",
  "铁木耳环",
  "链甲衫",
  "镶嵌小钻石的白金王冠",
  "镶嵌小钻石的白金项链",
  "镶嵌小钻石的白银项链",
  "镶嵌铜片的珍珠王冠",
  "镶嵌铜片的白金珠宝腰带",
  "长枪",
  "长柄镰刀",
  "阿克雷斯权杖",
  "阿克雷斯祈祷手镯",
  "青铜王冠",
  "额外弹药之轻型简易月石滑膛枪",
  "额外弹药之轻型简易月石长滑膛枪",
  "额外弹药之重型月石喷铅枪",
  "风岑翼杖",
  "饰纹嗜血毒蛇皮手套",
  "饰纹敏捷企鹅皮靴",
  "骑士剑",
  "骨制之三棱刺",
  "骨制之波刃短剑",
  "魅力企鹅板甲手套",
  "魅力企鹅环甲衫",
  "魅力企鹅皮上衣",
  "魅力企鹅皮护腿",
  "魅力企鹅链甲护腿",
  "魅力企鹅链甲护额",
  "魅力企鹅链甲衫",
  "魅力企鹅链甲靴",
  "魅力板甲手套",
  "魅力毒蛇板甲护腿",
  "魅力毒蛇板甲衫",
  "魅力毒蛇环甲衫",
  "魅力毒蛇皮靴",
  "魅力毒蛇链甲护腿",
  "魅力毒蛇链甲护额",
  "魅力毒蛇链甲衫",
  "魅力毒蛇链甲靴",
  "魅力火蜥蜴板甲靴",
  "魅力火蜥蜴环甲衫",
  "魅力火蜥蜴皮上衣",
  "魅力火蜥蜴皮护腿",
  "魅力火蜥蜴链甲手套",
  "魅力火蜥蜴链甲护腿",
  "魅力火蜥蜴链甲护额",
  "魅力火蜥蜴链甲衫",
  "魅力火蜥蜴链甲靴",
  "魅力环甲衫",
  "魅力链甲手套",
  "魅力链甲护腿",
  "魅力链甲护额",
  "魅力链甲衫",
  "魅力链甲靴",
  "魔力加持合成弓",
  "魔力加持火焰白蜡木弓",
  "魔力加持精准月刃弓",
  "魔法师徽章",
  "魔法强力东方斧",
  "魔法强力劈颅斧",
  "魔法愤怒矮人斧",
  "魔法矮人斧",
  "魔法精准劈颅斧",
  "魔法腰布",
  "鳞甲护胸",
  "鹤嘴锄",
  "黄金戒指",
  "黄金王冠",
  "黄金项链",
  "黑曜石戒指",
  "黑曜石耳环",
  "黑曜石臂章",
  "黑曜石项链",
    ];

    // ============================================================
    // 小工具
    // ============================================================
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // 标签页唯一 id（sessionStorage 跨导航保留、每标签页独立，
    // 用于配合 GM 存储实现多标签页互斥）
    const TAB_ID = (() => {
        let id = sessionStorage.getItem('wod_harvest_tab_id');
        if (!id) {
            id = 'tab_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
            sessionStorage.setItem('wod_harvest_tab_id', id);
        }
        return id;
    })();

    function gmSet(key, value) {
        try { GM_setValue(key, value); } catch (e) { console.error('[WoD收菜]', e); }
    }
    function gmGet(key, def) {
        try { return GM_getValue(key, def); } catch (e) { return def; }
    }

    // 导航探测：pagehide 在表单提交/链接点击导致页面卸载时触发
    let navStarted = false;
    window.addEventListener('pagehide', () => { navStarted = true; }, { once: true });

    // 点击一个可能触发刷新的元素，等待一段时间判断是否发生导航。
    // 关键：点击前先把 task 落盘。一旦导航开始，本页的定时器被销毁，
    // clickNav 的 Promise 可能永不 resolve，点击之后的 setTask 不会执行；
    // 新页面必须能从 GM 存储读到"点击后应有的状态"才能正确续跑。
    // expectNav=true：本次点击预期触发跳转（表单提交/链接）。若等待窗口
    // 内未跳转，不再操作本页（响应可能随时到达），视为 wait_page 并布防
    // 加载看门狗——若 STUCK_NAV_MS 后本页仍未卸载（服务器挂起），强制
    // 导航到物品页自救，新页面按已落盘的状态续跑
    // 出售任务的 step 以 sell_ 开头，落盘到独立的出售任务存储
    function isSellTask(t) { return t && typeof t.step === 'string' && t.step.startsWith('sell_'); }
    function saveTaskAny(t) { isSellTask(t) ? setSellTask(t) : setTask(t); }

    async function clickNav(task, el, expectNav = false, waitMs = NAV_WAIT_MS) {
        if (task) saveTaskAny(task);
        el.click();
        const start = Date.now();
        while (Date.now() - start < waitMs) {
            if (navStarted) return true;
            await sleep(150);
        }
        if (navStarted) return true;
        if (expectNav) {
            armLoadWatchdog();
            return true;
        }
        return false;
    }

    // 加载看门狗：本页发起导航后布防。若 STUCK_NAV_MS（10 分钟）后本页
    // 仍未卸载，说明响应迟迟未到（此时旧页面依然存活、定时器仍在跑），
    // 强制跳转物品页打断挂起的加载；跳转本身若也挂起则继续重试。
    // 恢复标记 recovered=true：新页面按落盘状态续跑前会先校验
    // （见 validateAfterRecovery），防止在筛选已失效的页面上误操作
    function armLoadWatchdog() {
        setTimeout(() => {
            if (navStarted) return;
            appendLog('WARNING', `${Math.round(STUCK_NAV_MS / 60000)} 分钟页面未跳转（服务器响应挂起？），强制导航到物品页恢复`);
            // 收菜、出售哪个在跑恢复哪个
            let task = getTask();
            if (task && task.running) {
                task.recovered = true;
                setTask(task);
            } else {
                task = getSellTask();
                if (task && task.running) {
                    task.recovered = true;
                    setSellTask(task);
                }
            }
            armLoadWatchdog(); // 再次布防：若这次跳转也挂起，继续重试
            location.href = ITEM_URL_PATH;
        }, STUCK_NAV_MS);
    }

    async function waitForSelector(sel, timeout = 30000) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            const el = document.querySelector(sel);
            if (el) return el;
            await sleep(300);
        }
        return null;
    }

    function isVisible(el) {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    // ============================================================
    // 日志（面板 + GM 存储，跨页面刷新保留）
    // ============================================================
    const MAX_LOG = 200;
    function appendLog(level, msg) {
        const symbols = { INFO: '✓', WARNING: '⚠', ERROR: '✗' };
        const ts = new Date().toTimeString().slice(0, 8);
        const line = `[${ts}] ${symbols[level] || '•'} ${msg}`;
        console.log('[WoD收菜]', line);
        const logs = gmGet(KEY_LOG, []);
        logs.push(line);
        if (logs.length > MAX_LOG) logs.splice(0, logs.length - MAX_LOG);
        gmSet(KEY_LOG, logs);
        if (window.__wodHarvestPanel && window.__wodHarvestPanel.appendLog) {
            window.__wodHarvestPanel.appendLog(line);
        }
    }

    // ============================================================
    // 页面状态检测（对应 get_hero_name / is_mentor_hero / _has_login_form / is_logged_in）
    // ============================================================

    function getHeroName() {
        const h1 = document.querySelector('h1');
        if (!h1) return '';
        return (h1.textContent || '').split(':')[0].trim();
    }

    function isMentorHero() {
        return location.href.includes('reason=mentor');
    }

    function loginFormInfo() {
        const username = document.querySelector('input#USERNAME[type="text"]');
        const password = document.querySelector('input#PASSWORT[type="password"]');
        const loginBtn = document.querySelector('input[name="LOGIN_BUTTON"][value="登陆"]');
        return {
            hasForm: !!(username && password) || !!loginBtn,
            onLoginPage: location.href.includes('login.php'),
        };
    }

    function isLoggedInPage() {
        if (!location.hostname.includes('world-of-dungeons')) return false;
        const info = loginFormInfo();
        if (info.hasForm || info.onLoginPage) return false;
        const path = location.pathname.replace(/\/+$/, '');
        if (path === '' || path === '/wod') return false;
        if (document.querySelector('img[alt="切换到下一个活跃的英雄"]')) return true;
        if (document.querySelector('input[name="item_3usage_item"][value="yes"]')) return true;
        return false;
    }

    function isItemsPage() {
        return location.pathname.includes(ITEM_URL_PATH);
    }

    // 错误页检测（对应 Python ensure_page_valid 的检测部分）：
    // 服务器 4xx/5xx 错误文档、连接重置文案、空白错误文档。
    // 注：浏览器级错误页（chrome-error:// 等）油猴脚本不会注入，
    // 那种页面只能靠其他标签页心跳超时接管
    function isErrorPage() {
        const title = document.title || '';
        const bodyText = document.body ? (document.body.textContent || '') : '';
        if (title.includes('无法访问此页面')) return true;
        if (title.includes('找不到') && title.includes('页面')) return true;   // 404
        if (/\b(404|500|502|503|504)\b/.test(title) && !bodyText.includes('world-of-dungeons')) return true;
        if (bodyText.includes('已重置连接')) return true;
        if (bodyText.includes('无法访问此网站')) return true;
        // 游戏域名下几乎空白的文档（WoD 正常页面内容远大于此）
        if (location.hostname.includes('world-of-dungeons') &&
            !document.querySelector('h1') && !document.querySelector('form') &&
            bodyText.trim().length < 50) return true;
        return false;
    }

    // ============================================================
    // 任务状态机
    // ============================================================
    // task 结构：
    // {
    //   running: true,
    //   step: 'goto_items',      // 当前步骤（见 FLOW）
    //   sub: null,               // 步骤内子状态（跨页面刷新续跑）
    //   cleanPhase: null,        // 清理背包子相位（null/page_info/goto_page2/drop/back_page1/pick/verify）
    //   cleanSub: null,          // drop 相位内子状态（null/setter_clicked）
    //   cleanRound: 1,           // 清理轮次（1..2）
    //   processed: ['英雄A'],    // 已处理英雄名（循环结束判定）
    //   startedAt: ts,
    //   noProgress: 0,           // 连续无进展计数（导师跳过/出错）
    //   pageRetries: 0,          // 错误页/404 连续重试计数（上限 PAGE_RETRY_MAX）
    //   scheduled: false,        // 是否由定时触发
    // }
    //
    // 步骤返回值：
    //   'advance'   流程推进到下一步（同页继续）
    //   'repeat'    重跑当前步骤（子状态已更新）
    //   'wait_page' 已触发导航，本页终止，新页面 document-end 时续跑
    //   'done'      整个收菜流程结束
    //   'halt'      异常终止（步骤内已记录日志）

    const FLOW = {
        goto_items: 'loop_begin',
        loop_begin: 'clean_backpack',
        clean_backpack: 'filter_consumables',
        filter_consumables: 'move_group_2',
        move_group_2: 'filter_pieces',
        filter_pieces: 'move_group',
        move_group: 'dungeon_time',
        dungeon_time: 'next_hero',
        next_hero: 'loop_begin',
    };

    function getTask() { return gmGet(KEY_TASK, null); }
    function setTask(t) { gmSet(KEY_TASK, t); }
    function clearTask() { gmSet(KEY_TASK, null); }

    // ----- 多标签页所有权（防止多个 WoD 标签页同时跑任务） -----
    function acquireOwnership() {
        const owner = gmGet(KEY_OWNER, null);
        if (owner && owner.id !== TAB_ID && Date.now() - (owner.heartbeat || 0) < HEARTBEAT_STALE_MS) {
            return false;
        }
        if (owner && owner.id !== TAB_ID) {
            appendLog('WARNING', `接管任务所有权（原持有页 ${owner.id} 心跳超时）`);
        }
        gmSet(KEY_OWNER, { id: TAB_ID, heartbeat: Date.now() });
        return true;
    }
    function releaseOwnership() { gmSet(KEY_OWNER, null); }
    function heartbeat() {
        const owner = gmGet(KEY_OWNER, null);
        if (owner && owner.id === TAB_ID) {
            gmSet(KEY_OWNER, { id: TAB_ID, heartbeat: Date.now() });
        }
    }
    setInterval(heartbeat, 10000);

    // ----- 任务入口 -----
    function startHarvest(scheduled) {
        if (!isLoggedInPage()) {
            appendLog('ERROR', '当前未登录或不在游戏页面，请先登录后再开始收菜');
            return false;
        }
        const existing = getTask();
        if (existing && existing.running) {
            appendLog('WARNING', '已有任务在进行中，如需重开请先停止');
            return false;
        }
        if (!acquireOwnership()) {
            appendLog('WARNING', '任务正由其他标签页执行，本次忽略');
            return false;
        }
        appendLog('INFO', scheduled ? '定时收菜开始...' : '开始收菜...');
        setTask({
            running: true,
            step: 'goto_items',
            sub: null,
            cleanPhase: null,
            cleanSub: null,
            cleanRound: 1,
            processed: [],
            startedAt: Date.now(),
            noProgress: 0,
            pageRetries: 0,
            scheduled: !!scheduled,
        });
        runNextStep();
        return true;
    }

    function stopHarvest(reason) {
        clearTask();
        releaseOwnership();
        appendLog('INFO', `收菜已停止${reason ? '：' + reason : ''}`);
        if (window.__wodHarvestPanel) window.__wodHarvestPanel.refreshStatus();
    }

    // ----- 调度器 -----
    async function runNextStep() {
        heartbeat();
        let task = getTask();
        if (!task || !task.running) return;

        // 总超时保护
        if (Date.now() - task.startedAt > TASK_TIMEOUT_MS) {
            appendLog('ERROR', '任务超时（6小时），自动终止');
            stopHarvest('超时');
            return;
        }

        let result;
        try {
            result = await execStep(task);
        } catch (e) {
            appendLog('ERROR', `步骤 ${task.step} 出错: ${e && e.message}`);
            console.error('[WoD收菜]', e);
            // 对应 Python 容错：出错仍尝试切到下一个英雄。
            // 必须先改 step 再点击——clickNav 点击前落盘，若导航开始，
            // 新页面读到的就是 loop_begin 而不是重试刚失败的步骤
            task.noProgress++;
            task.step = 'loop_begin';
            task.sub = null;
            if (await clickNextHero(task)) {
                return; // 等新页面
            }
            stopHarvest('出错且无法切换英雄');
            return;
        }

        if (result === 'halt') {
            stopHarvest('流程异常终止');
            return;
        }
        if (result === 'done') {
            finishHarvest(task);
            return;
        }
        if (result === 'advance') {
            // 离开清理步骤时复位清理子状态，避免污染下一个英雄
            if (task.step === 'clean_backpack') {
                task.cleanPhase = null;
                task.cleanSub = null;
                task.cleanRound = 1;
            }
            task.step = FLOW[task.step] || 'loop_begin';
            task.sub = null; // 进入新步骤，清除子状态
        }
        // advance/repeat/wait_page 统一落盘：
        // wait_page 场景下步骤内部已把"点击后的下一状态"写进 task，
        // 新页面凭这份存档续跑
        setTask(task);

        if (result === 'wait_page') return;
        await sleep(STEP_GAP_MS);
        runNextStep(); // advance / repeat 同页继续
    }

    function finishHarvest(task) {
        const mins = Math.max(1, Math.round((Date.now() - task.startedAt) / 60000));
        appendLog('INFO', `收菜完成! 共处理 ${task.processed.length} 个英雄，耗时 ${mins} 分钟`);
        clearTask();
        releaseOwnership();
        if (window.__wodHarvestPanel) window.__wodHarvestPanel.refreshStatus();
        if (gmGet(KEY_SCHED_ON, false)) scheduleNext();
    }

    // ============================================================
    // 各步骤实现（与 wod_scheduler.py 方法一一对应）
    // ============================================================

    async function execStep(task) {
        switch (task.step) {
            case 'goto_items': return stepGotoItems();
            case 'loop_begin': return stepLoopBegin(task);
            case 'clean_backpack': return stepCleanBackpack(task);
            case 'filter_consumables': return stepFilter(task, 'consumables');
            case 'move_group_2': return stepMove(task, 'go_group_2', '团队仓库');
            case 'filter_pieces': return stepFilter(task, 'pieces');
            case 'move_group': return stepMove(task, 'go_group', '宝库');
            case 'dungeon_time': return stepDungeonTime();
            case 'next_hero': return stepNextHero(task);
            default:
                appendLog('ERROR', `未知步骤: ${task.step}，重置到循环起点`);
                return 'advance';
        }
    }

    // 对应 navigate_to_items
    async function stepGotoItems() {
        if (!isItemsPage()) {
            appendLog('INFO', '正在导航到物品页面...');
            armLoadWatchdog(); // 跳转挂起时强制重试
            location.href = ITEM_URL_PATH;
            return 'wait_page';
        }
        await sleep(EXTRA_WAIT_MS);
        return 'advance';
    }

    // 对应 process_all_heroes 循环头 + process_hero 开头
    async function stepLoopBegin(task) {
        const heroName = getHeroName();
        if (!heroName) {
            if (!isItemsPage()) {
                armLoadWatchdog();
                location.href = ITEM_URL_PATH;
                return 'wait_page';
            }
            appendLog('ERROR', '在物品页面无法获取英雄名称，终止');
            return 'halt';
        }
        if (task.processed.includes(heroName)) {
            appendLog('INFO', `回到已处理英雄: ${heroName}`);
            appendLog('INFO', `循环结束，共处理 ${task.processed.length} 个英雄: ${task.processed.join(', ')}`);
            return 'done';
        }
        if (task.noProgress > NO_PROGRESS_LIMIT) {
            appendLog('ERROR', `连续 ${task.noProgress} 次无进展，终止（可能英雄持续失败或全部为导师英雄）`);
            return 'halt';
        }
        appendLog('INFO', `处理英雄: ${heroName}`);
        if (isMentorHero()) {
            appendLog('INFO', '  -> 跳过导师英雄');
            task.noProgress++;
            task.sub = 'mentor_switching';
            if (await clickNextHero(task)) return 'wait_page';
            // 导航未确认：留在 loop_begin 重查（页面若已跳，本段随页面卸载终止）
            task.sub = null;
            appendLog('WARNING', '导师英雄切换导航未确认，重试检查');
            return 'repeat';
        }
        // 上个页面点击切换后未探测到导航的兜底：忽略残留 sub
        if (task.sub === 'mentor_switching') task.sub = null;
        return 'advance';
    }

    // 对应 clean_backpack（拆为可跨页续跑的子相位）
    async function stepCleanBackpack(task) {
        await sleep(EXTRA_WAIT_MS);
        const bodyText = document.body ? (document.body.textContent || '') : '';

        if (task.cleanPhase === null) {
            if (!bodyText.includes('不得不抛弃')) {
                appendLog('INFO', '背包未超载，无需清理');
                return 'advance';
            }
            appendLog('INFO', '检测到背包超载，开始清理...');
            task.cleanPhase = 'page_info';
            return 'repeat';
        }

        switch (task.cleanPhase) {

            // 观察分页信息（对应 Python 第3步）
            case 'page_info': {
                const row = document.querySelector('td.paginator_row');
                if (!row) {
                    appendLog('WARNING', '无 paginator_row，跳过清理');
                    task.cleanPhase = null;
                    return 'advance';
                }
                const pageBtns = row.querySelectorAll("input[name^='ITEMS_GEFUNDEN_PAGE'], input[name='dummy']");
                const cur = row.querySelector('.paginator_selected');
                const curPage = cur ? ((cur.getAttribute('value') || '').match(/=(\d+)=/) || [])[1] : null;
                appendLog('INFO', `页面信息: 总页数=${pageBtns.length}, 当前页=${curPage || '未知'}`);
                // 价格降序时低价物品在第2页
                if (curPage !== '2' && pageBtns.length >= 2) {
                    task.cleanPhase = 'goto_page2';
                } else {
                    task.cleanPhase = 'drop';
                    task.cleanSub = null;
                    task.cleanRound = 1;
                }
                return 'repeat';
            }

            // 切到第2页（表单提交，会刷新）
            case 'goto_page2': {
                appendLog('INFO', '切换到第2页');
                const btn = document.querySelector('input[name="ITEMS_GEFUNDEN_PAGE[2]"]');
                task.cleanPhase = 'drop';
                task.cleanSub = null;
                task.cleanRound = 1;
                if (!btn) return 'repeat';
                if (await clickNav(task, btn, true)) return 'wait_page';
                return 'repeat';
            }

            // 丢弃全选 + 应用改动，重复两轮（对应 Python 第7-8步）
            case 'drop': {
                if (!bodyText.includes('不把沉重的背包清理一番')) {
                    appendLog('INFO', '已进入仓库页面，无需继续清理');
                    task.cleanPhase = null;
                    return 'advance';
                }
                if (task.cleanSub !== 'setter_clicked') {
                    appendLog('INFO', `第${task.cleanRound}次：点击丢弃全选按钮`);
                    const setter = document.querySelector('input[name="SellItemsFound_setter[1]"]');
                    if (setter) {
                        task.cleanSub = 'setter_clicked';
                        if (await clickNav(task, setter)) return 'wait_page';
                        await sleep(500);
                    } else {
                        appendLog('WARNING', '丢弃全选按钮未找到，尝试直接应用');
                    }
                }
                appendLog('INFO', `第${task.cleanRound}次：点击应用改动`);
                const apply = document.querySelector('input[value="应用改动"]');
                if (!apply) {
                    appendLog('WARNING', '应用改动按钮未找到，跳过清理');
                    task.cleanPhase = null;
                    return 'advance';
                }
                task.cleanSub = null;
                if (task.cleanRound >= 2) {
                    task.cleanPhase = 'back_page1';
                } else {
                    task.cleanRound++;
                }
                if (await clickNav(task, apply, true)) return 'wait_page';
                return 'repeat';
            }

            // 回到第1页（对应 Python 第9步）
            case 'back_page1': {
                appendLog('INFO', '两次清理完成，回到第1页查看是否仍需丢弃物品');
                const btn = document.querySelector('input[name="ITEMS_GEFUNDEN_PAGE[1]"]');
                task.cleanPhase = 'pick';
                if (!btn) return 'repeat';
                if (await clickNav(task, btn, true)) return 'wait_page';
                return 'repeat';
            }

            // 从下向上勾选 N 件丢弃（对应 Python 第10步）
            case 'pick': {
                const match = bodyText.match(/不得不抛弃(\d+)件物品/);
                const needDrop = match ? parseInt(match[1], 10) : 0;
                if (!needDrop) {
                    appendLog('INFO', '不需要再丢弃物品');
                    task.cleanPhase = null;
                    return 'advance';
                }
                appendLog('INFO', `需要丢弃${needDrop}件物品`);
                const picked = pickItemsFromBottom(needDrop);
                if (picked.length) {
                    appendLog('INFO', `从下往上勾选了 ${picked.length} 件物品：`);
                    picked.forEach((t, i) => appendLog('INFO', `  ${i + 1}. ${t}`));
                } else {
                    appendLog('WARNING', `未能勾选任何物品（need_drop=${needDrop}）`);
                }
                const apply = document.querySelector('input[value="应用改动"]');
                if (!apply) {
                    appendLog('WARNING', '应用改动按钮未找到，跳过清理');
                    task.cleanPhase = null;
                    return 'advance';
                }
                task.cleanPhase = 'verify';
                if (await clickNav(task, apply, true)) return 'wait_page';
                return 'repeat';
            }

            // 验证清理结果（对应 Python 第12步）
            case 'verify': {
                const still = (document.body.textContent || '').includes('不得不抛弃');
                if (still) {
                    appendLog('WARNING', '清理后仍然超载');
                } else {
                    appendLog('INFO', '清理背包完成，已进入仓库页面');
                }
                task.cleanPhase = null;
                return 'advance';
            }
        }

        task.cleanPhase = null; // 未知相位复位
        return 'advance';
    }

    // Python 第10步 evaluate 的 JS 移植：从下往上勾选 N 件物品
    function pickItemsFromBottom(needDrop) {
        const paragraphs = document.querySelectorAll('p');
        let targetParagraph = null;
        for (const p of paragraphs) {
            if (p.textContent.includes('不把沉重的背包清理一番')) {
                targetParagraph = p;
                break;
            }
        }
        if (!targetParagraph) return [];
        let current = targetParagraph.nextElementSibling;
        while (current) {
            if (current.tagName === 'TABLE' && current.classList.contains('content_table')) break;
            current = current.nextElementSibling;
        }
        if (!current) return [];
        const rows = Array.from(current.querySelectorAll('tr'));
        const rowsWithCheckbox = [];
        rows.forEach(row => {
            const checkbox = row.querySelector("input[name^='SellItemsFound[']:not([name*='setter'])");
            if (checkbox) rowsWithCheckbox.push(checkbox);
        });
        const picked = [];
        for (let i = 1; i <= needDrop && i <= rowsWithCheckbox.length; i++) {
            const cb = rowsWithCheckbox[rowsWithCheckbox.length - i];
            cb.checked = true;
            const rowText = (cb.closest('tr') ? cb.closest('tr').textContent : '').replace(/\s+/g, ' ').trim();
            picked.push(rowText);
        }
        return picked;
    }

    // 对应 filter_seconds（耗材） / filter_pieces（镶嵌材料）
    // 子状态: null →(勾选筛选框)→ 'cb_done' →(点开始搜索)→ 'searched' →(确认)→ 完成
    async function stepFilter(task, kind) {
        await sleep(EXTRA_WAIT_MS);

        if (task.sub === 'searched') {
            appendLog('INFO', kind === 'consumables' ? '筛选耗材完成' : '筛选镶嵌材料完成');
            return 'advance';
        }

        // 勾选筛选框（本页或上个页面已点击导航到的新页面）
        if (task.sub !== 'cb_done') {
            if (kind === 'consumables') {
                appendLog('INFO', '正在筛选耗材...');
                const cb = await waitForSelector('input[name="item_3usage_item"][value="yes"]', 60000);
                if (!cb) {
                    appendLog('WARNING', '筛选复选框未找到，跳过');
                    return 'advance';
                }
                if (!cb.checked) {
                    task.sub = 'cb_done'; // 若此点击触发刷新，新页面续跑点搜索
                    if (await clickNav(task, cb)) return 'wait_page';
                    await sleep(500);
                }
            } else {
                appendLog('INFO', '正在筛选镶嵌材料...');
                const cb = await waitForSelector('input[name="item_3usage_item"][value=""]', 60000);
                if (!cb) {
                    appendLog('WARNING', '镶嵌材料筛选框未找到，跳过');
                    return 'advance';
                }
                if (!cb.checked) {
                    task.sub = 'cb_done';
                    if (await clickNav(task, cb)) return 'wait_page';
                    await sleep(500);
                }
            }
        }

        // 镶嵌材料：还需设置镶嵌槽下拉框（新页面续跑时同样执行）
        if (kind === 'pieces') {
            const sel = document.querySelector('select[name="item_3sockets"]');
            if (sel) {
                sel.value = '-1';
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                await sleep(500);
            } else {
                appendLog('WARNING', '镶嵌槽筛选下拉框未找到');
            }
        }

        // 点击"开始搜索"（Python 无条件执行此步，即使勾选框点击已刷新页面）
        const searchBtn = findSearchButton();
        if (!searchBtn) {
            appendLog('WARNING', '搜索按钮未找到，跳过');
            return 'advance';
        }
        task.sub = 'searched';
        if (await clickNav(task, searchBtn, true)) return 'wait_page';
        // 搜索点击未导航（异常），直接视为完成
        return 'advance';
    }

    // "开始搜索"按钮：input 优先，其次文本匹配
    function findSearchButton() {
        for (const inp of document.querySelectorAll('input[type="submit"], input[type="button"]')) {
            if ((inp.value || '').trim() === '开始搜索') return inp;
        }
        for (const el of document.querySelectorAll('a, button, span.link')) {
            if ((el.textContent || '').trim() === '开始搜索') return el;
        }
        return null;
    }

    // 对应 move_to_warehouse（_click_first_checkbox + 下拉选择 + 应用）
    // 子状态: null →(点全选)→ 'selected' →(点应用)→ 'applied' →(确认)→ 完成
    async function stepMove(task, targetValue, targetName) {
        if (task.sub === 'applied') {
            appendLog('INFO', `全选并移动到${targetName}完成`);
            return 'advance';
        }

        if (task.sub === null) {
            appendLog('INFO', `准备将选中物品移动到${targetName}`);
            // thead 与 tfoot 有同名复选框，指定 thead（对应 Python 的 XPath）
            const checkbox = document.querySelector('thead input[name="doEquipItem_setter[2]"]');
            if (!checkbox) {
                appendLog('INFO', `当前页面没有可操作的物品，跳过移动到${targetName}`);
                return 'advance';
            }
            appendLog('INFO', '>>>全选');
            task.sub = 'selected';
            if (!checkbox.checked) {
                if (await clickNav(task, checkbox)) return 'wait_page';
                await sleep(500);
            }
        }

        // sub === 'selected'：下拉选择目标位置
        const sel = document.querySelector('thead select[name="dummy"]');
        if (!sel) {
            appendLog('WARNING', '位置下拉框未找到，跳过');
            task.sub = null;
            return 'advance';
        }
        appendLog('INFO', '>>>移动...');
        sel.value = targetValue;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(600);

        const apply = document.querySelector('input[value="应用改动"]');
        if (!apply) {
            appendLog('WARNING', '应用改动按钮未找到，跳过');
            task.sub = null;
            return 'advance';
        }
        appendLog('INFO', '>>>应用...');
        task.sub = 'applied';
        if (await clickNav(task, apply, true)) return 'wait_page';
        return 'advance';
    }

    // 对应 set_dungeon_time（AJAX，不刷新页面；
    // 若实际触发了导航，新页面重入本步骤时按钮已消失，自然跳过）
    async function stepDungeonTime() {
        await sleep(600);
        const btn = document.querySelector('input[name="reduce_dungeon_time"]');
        const timeBefore = (document.getElementById('gadgetNextdungeonTime') || {}).textContent || '';
        if (timeBefore) appendLog('INFO', `地城时间（设置前）: ${timeBefore}`);
        if (!btn || !isVisible(btn)) {
            appendLog('INFO', '跳过设置地城时间: 无减少时间按钮');
            return 'advance';
        }
        appendLog('INFO', '点击减少地城时间按钮...');
        btn.click();
        await sleep(1500);
        const timeAfter = (document.getElementById('gadgetNextdungeonTime') || {}).textContent || '';
        if (timeAfter) appendLog('INFO', `地城时间（设置后）: ${timeAfter}`);
        if (!isVisible(document.querySelector('input[name="reduce_dungeon_time"]'))) {
            appendLog('INFO', '加速成功');
        }
        return 'advance';
    }

    // 对应 switch_to_next_hero + process_hero 结尾
    // 子状态: null → 'switching'（切换点击已发出；新页面重入本步骤时
    // 直接流转到 loop_begin，避免把新英雄误标记为已处理）
    async function stepNextHero(task) {
        if (task.sub === 'switching') {
            task.sub = null;
            return 'advance';
        }
        const heroName = getHeroName();
        if (heroName && !task.processed.includes(heroName)) {
            task.processed.push(heroName);
            task.noProgress = 0; // 成功处理一个英雄，重置无进展计数
        }
        appendLog('INFO', `处理英雄完成: ${heroName}`);
        task.sub = 'switching';
        const clicked = await clickNextHero(task);
        if (!clicked) {
            // 未探测到导航：可能按钮确实不在，也可能导航较慢。
            // 回退到 loop_begin——若页面没跳，loop_begin 会发现当前英雄
            // 已在 processed 里而干净收尾；若页面其实跳了，本段代码
            // 随页面卸载一同终止，不影响新页面续跑。
            task.sub = null;
            appendLog('WARNING', '切换英雄导航未确认，回到循环头检查');
            return 'advance';
        }
        return 'wait_page';
    }

    // 点击"切换到下一个活跃的英雄"（链接导航，预期必跳转；
    // 挂起时由加载看门狗恢复）
    async function clickNextHero(task) {
        const img = document.querySelector('img[alt="切换到下一个活跃的英雄"]');
        if (!img) {
            appendLog('WARNING', '切换英雄按钮未找到');
            return false;
        }
        return clickNav(task, img, true);
    }

    // ============================================================
    // 自动出售（按 SELLABLE_ITEMS 清单轮询所有英雄，对应
    // wod_scheduler.py 的 sell_sellable_items / sell_all_heroes）
    // ============================================================
    // sell_task 结构（与收菜 task 同构）：
    // {
    //   running: true,
    //   step: 'sell_goto_items' | 'sell_loop_begin' | 'sell_round'
    //       | 'sell_confirm' | 'sell_next_hero',
    //   sub: null | 'applied'（应用改动已点击）| 'confirmed'（OK 已点击）
    //       | 'switching'（切换英雄已点击）,
    //   processed: ['英雄A'],   // 已处理英雄名（循环结束判定）
    //   totalSold: 0,           // 累计卖出件数
    //   roundSold: 0,           // 本轮圈选件数（跨页面带到确认步骤计数）
    //   startedAt: ts,
    //   noProgress: 0,
    //   pageRetries: 0,
    // }
    const SELL_FLOW = {
        sell_goto_items: 'sell_loop_begin',
        sell_loop_begin: 'sell_round',
        sell_round: 'sell_confirm',
        sell_confirm: 'sell_next_hero',
        sell_next_hero: 'sell_loop_begin',
    };

    function getSellTask() { return gmGet(KEY_SELL_TASK, null); }
    function setSellTask(t) { gmSet(KEY_SELL_TASK, t); }
    function clearSellTask() { gmSet(KEY_SELL_TASK, null); }

    // 出售任务的所有权（与收菜共用 KEY_OWNER 心跳，互斥防并发）
    function acquireSellOwnership() {
        const owner = gmGet(KEY_OWNER, null);
        if (owner && owner.id !== TAB_ID && Date.now() - (owner.heartbeat || 0) < HEARTBEAT_STALE_MS) {
            return false;
        }
        if (owner && owner.id !== TAB_ID) {
            appendLog('WARNING', `接管任务所有权（原持有页 ${owner.id} 心跳超时）`);
        }
        gmSet(KEY_OWNER, { id: TAB_ID, heartbeat: Date.now() });
        return true;
    }

    function startSell() {
        if (!isLoggedInPage()) {
            appendLog('ERROR', '当前未登录或不在游戏页面，请先登录后再开始出售');
            return false;
        }
        if (getTask() && getTask().running) {
            appendLog('WARNING', '收菜任务进行中，请等收菜结束再出售');
            return false;
        }
        const existing = getSellTask();
        if (existing && existing.running) {
            appendLog('WARNING', '已有出售任务在进行中，如需重开请先停止');
            return false;
        }
        if (!acquireSellOwnership()) {
            appendLog('WARNING', '任务正由其他标签页执行，本次忽略');
            return false;
        }
        appendLog('INFO', `开始自动出售（清单 ${SELLABLE_ITEMS.length} 条）...`);
        setSellTask({
            running: true,
            step: 'sell_goto_items',
            sub: null,
            processed: [],
            totalSold: 0,
            roundSold: 0,
            startedAt: Date.now(),
            noProgress: 0,
            pageRetries: 0,
        });
        runNextSellStep();
        return true;
    }

    function stopSell(reason) {
        clearSellTask();
        releaseOwnership();
        appendLog('INFO', `出售已停止${reason ? '：' + reason : ''}`);
        if (window.__wodHarvestPanel) window.__wodHarvestPanel.refreshStatus();
    }

    async function runNextSellStep() {
        heartbeat();
        let task = getSellTask();
        if (!task || !task.running) return;

        // 总超时保护（与收菜共用上限）
        if (Date.now() - task.startedAt > TASK_TIMEOUT_MS) {
            appendLog('ERROR', '出售任务超时（6小时），自动终止');
            stopSell('超时');
            return;
        }

        let result;
        try {
            result = await execSellStep(task);
        } catch (e) {
            appendLog('ERROR', `出售步骤 ${task.step} 出错: ${e && e.message}`);
            console.error('[WoD收菜]', e);
            task.noProgress++;
            task.step = 'sell_loop_begin';
            task.sub = null;
            if (await clickNextHero(task)) {
                task.sub = 'switching';
                setSellTask(task);
                return; // 等新页面
            }
            stopSell('出错且无法切换英雄');
            return;
        }

        if (result === 'halt') {
            stopSell('出售流程异常终止');
            return;
        }
        if (result === 'done') {
            finishSell(task);
            return;
        }
        if (result === 'advance') {
            task.step = SELL_FLOW[task.step] || 'sell_loop_begin';
            task.sub = null;
        }
        setSellTask(task);

        if (result === 'wait_page') return;
        await sleep(SELL_ROUND_GAP_MS);
        runNextSellStep();
    }

    function finishSell(task) {
        const mins = Math.max(1, Math.round((Date.now() - task.startedAt) / 60000));
        appendLog('INFO', `出售完成! 共处理 ${task.processed.length} 个英雄，卖出 ${task.totalSold} 件，耗时 ${mins} 分钟`);
        clearSellTask();
        releaseOwnership();
        if (window.__wodHarvestPanel) window.__wodHarvestPanel.refreshStatus();
    }

    async function execSellStep(task) {
        switch (task.step) {
            case 'sell_goto_items': return sellStepGotoItems();
            case 'sell_loop_begin': return sellStepLoopBegin(task);
            case 'sell_round': return sellStepRound(task);
            case 'sell_confirm': return sellStepConfirm(task);
            case 'sell_next_hero': return sellStepNextHero(task);
            default:
                appendLog('ERROR', `未知出售步骤: ${task.step}，重置到循环起点`);
                return 'advance';
        }
    }

    async function sellStepGotoItems() {
        if (!isItemsPage()) {
            appendLog('INFO', '正在导航到物品页面...');
            armLoadWatchdog();
            location.href = ITEM_URL_PATH;
            return 'wait_page';
        }
        await sleep(EXTRA_WAIT_MS);
        return 'advance';
    }

    // 对应 sell_all_heroes 的循环头（参考 stepLoopBegin）
    async function sellStepLoopBegin(task) {
        const heroName = getHeroName();
        if (!heroName) {
            if (!isItemsPage()) {
                armLoadWatchdog();
                location.href = ITEM_URL_PATH;
                return 'wait_page';
            }
            appendLog('ERROR', '在物品页面无法获取英雄名称，终止');
            return 'halt';
        }
        if (task.processed.includes(heroName)) {
            appendLog('INFO', `回到已处理英雄: ${heroName}`);
            appendLog('INFO', `循环结束，共处理 ${task.processed.length} 个英雄`);
            return 'done';
        }
        if (task.noProgress > NO_PROGRESS_LIMIT) {
            appendLog('ERROR', `连续 ${task.noProgress} 次无进展，终止`);
            return 'halt';
        }
        appendLog('INFO', `【出售】处理英雄: ${heroName}（累计卖出 ${task.totalSold} 件）`);
        if (isMentorHero()) {
            appendLog('INFO', '  -> 跳过导师英雄');
            task.noProgress++;
            task.sub = 'switching';
            if (await clickNextHero(task)) return 'wait_page';
            task.sub = null;
            appendLog('WARNING', '导师英雄切换导航未确认，重试检查');
            return 'repeat';
        }
        return 'advance';
    }

    // 对应 sell_sellable_items 的圈选（_check_sellable_page）：
    // 勾选所有匹配清单的物品（不清除已有勾选），有匹配则点应用改动
    async function sellStepRound(task) {
        await sleep(SELL_ROUND_GAP_MS);

        if (task.sub !== 'applied') {
            const picked = pickSellableItems();
            if (!picked.length) {
                appendLog('INFO', `【出售】${getHeroName()} 无匹配清单的物品`);
                return 'advance';
            }
            task.roundSold = picked.length;
            const uniq = [...new Set(picked)];
            const preview = uniq.slice(0, 8).join(', ') + (uniq.length > 8 ? '...' : '');
            appendLog('INFO', `【出售】圈选 ${picked.length} 件: ${preview}`);

            const apply = document.querySelector('input[value="应用改动"]');
            if (!apply) {
                appendLog('WARNING', '【出售】应用改动按钮未找到，跳过本英雄');
                return 'advance';
            }
            task.sub = 'applied';
            if (await clickNav(task, apply, true)) return 'wait_page';
            // 点击未导航（异常）：本页继续走确认步骤
        }
        // sub === 'applied'：本页继续（等待确认步骤检查确认按钮）
        return 'advance';
    }

    // 勾选匹配 SELLABLE_ITEMS 的物品（对应 Python _check_sellable_page）
    function pickSellableItems() {
        const pats = SELLABLE_ITEMS.map(p => { try { return new RegExp(p); } catch (e) { return new RegExp(p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')); } });
        const picked = [];
        document.querySelectorAll('input[type=checkbox][name^="SellItems"]').forEach(cb => {
            if (cb.name.includes('setter') || cb.checked || cb.disabled) return;
            const row = cb.closest('tr');
            if (!row) return;
            const a = row.querySelector('a[href*="item_instance_id"]');
            if (!a) return;
            const t = (a.textContent || '').replace(/!/g, '').trim();
            if (t && pats.some(p => p.test(t))) { cb.checked = true; picked.push(t); }
        });
        return picked;
    }

    // 对应确认页点 OK：应用改动后若出现 sellconfirm 按钮则点击（真正卖出），
    // 没有则视为物品实际不可卖（服务器拒绝），继续下一英雄
    async function sellStepConfirm(task) {
        await sleep(SELL_ROUND_GAP_MS);

        if (task.sub === 'confirmed') {
            appendLog('INFO', `【出售】已确认卖出 ${task.roundSold} 件（累计 ${task.totalSold}）`);
            task.roundSold = 0;
            return 'advance';
        }

        const ok = document.querySelector('input[name="sellconfirm"]');
        if (!ok) {
            // 没有确认页：可能物品被服务器拒绝，或"应用改动"根本没提交成功。
            // 无进展计数 +1 防死循环；roundSold 复位避免重复累计
            task.noProgress++;
            task.roundSold = 0;
            appendLog('WARNING', '【出售】未出现出售确认页，回到物品页继续');
            armLoadWatchdog();
            location.href = ITEM_URL_PATH;
            return 'wait_page';
        }

        appendLog('INFO', '【出售】出现确认页，点击 OK...');
        task.totalSold += task.roundSold;
        task.sub = 'confirmed';
        if (await clickNav(task, ok, true)) return 'wait_page';
        await sleep(1000);
        return 'advance';
    }

    // 对应 sell_all_heroes 的切换（参考 stepNextHero）
    async function sellStepNextHero(task) {
        if (task.sub === 'switching') {
            task.sub = null;
            return 'advance';
        }
        const heroName = getHeroName();
        if (heroName && !task.processed.includes(heroName)) {
            task.processed.push(heroName);
            task.noProgress = 0;
        }
        task.sub = 'switching';
        const clicked = await clickNextHero(task);
        if (!clicked) {
            task.sub = null;
            appendLog('WARNING', '切换英雄导航未确认，回到循环头检查');
            return 'advance';
        }
        return 'wait_page';
    }

    // 出售任务的页面加载续跑入口（onPageLoaded 里调用）
    function onSellPageLoaded() {
        const task = getSellTask();
        if (!task || !task.running) return;

        // 会话过期检测
        const info = loginFormInfo();
        if (info.hasForm || info.onLoginPage) {
            appendLog('ERROR', '会话已过期（跳转到登录页），出售任务终止。');
            stopSell('登录已过期');
            return;
        }

        const owner = gmGet(KEY_OWNER, null);
        if (owner && owner.id !== TAB_ID && Date.now() - (owner.heartbeat || 0) < HEARTBEAT_STALE_MS) {
            return; // 其他标签页在执行
        }
        acquireSellOwnership();

        // 错误页检测：刷新重试，上限 PAGE_RETRY_MAX 次
        if (isErrorPage()) {
            const n = (task.pageRetries || 0) + 1;
            if (n > PAGE_RETRY_MAX) {
                appendLog('ERROR', `连续 ${PAGE_RETRY_MAX} 次加载到错误页，出售任务终止。当前 URL: ${location.href}`);
                stopSell('页面持续加载失败');
                return;
            }
            task.pageRetries = n;
            setSellTask(task);
            appendLog('WARNING', `检测到错误页面，尝试刷新 (${n}/${PAGE_RETRY_MAX})...`);
            armLoadWatchdog();
            setTimeout(() => location.reload(), 2000);
            return;
        }
        if (task.pageRetries) {
            task.pageRetries = 0;
            setSellTask(task);
        }

        // 看门狗恢复后的校正：出售各步骤幂等（圈选重复无副作用、
        // 无确认页自动回物品页），回到循环起点重做即可
        if (task.recovered) {
            task.recovered = false;
            if (task.step !== 'sell_goto_items' && task.step !== 'sell_loop_begin') {
                task.step = 'sell_loop_begin';
                task.sub = null;
                appendLog('WARNING', '恢复：回到当前英雄出售流程起点重做');
            }
            setSellTask(task);
        }

        appendLog('INFO', `页面就绪，继续出售步骤: ${task.step}${task.sub ? '/' + task.sub : ''}`);
        setTimeout(() => runNextSellStep(), EXTRA_WAIT_MS);
    }

    // ============================================================
    // 定时任务（对应 GUI 的启动定时 / 间隔设置）
    // ============================================================

    function getIntervalMin() {
        const v = parseFloat(gmGet(KEY_INTERVAL, DEFAULT_INTERVAL_MIN));
        return (isNaN(v) || v <= 0) ? DEFAULT_INTERVAL_MIN : v;
    }

    function formatTime(ts) {
        const d = new Date(ts);
        const p = n => String(n).padStart(2, '0');
        return `${p(d.getHours())}:${p(d.getMinutes())}`;
    }

    function scheduleNext() {
        const next = Date.now() + getIntervalMin() * 60 * 1000;
        gmSet(KEY_NEXT_RUN, next);
        appendLog('INFO', `下次收菜: ${formatTime(next)}`);
        if (window.__wodHarvestPanel) window.__wodHarvestPanel.refreshStatus();
    }

    function startScheduler() {
        gmSet(KEY_SCHED_ON, true);
        appendLog('INFO', `定时收菜已启动，间隔 ${getIntervalMin()} 分钟（立即执行一次）`);
        if (window.__wodHarvestPanel) window.__wodHarvestPanel.refreshStatus();
        startHarvest(true);
    }

    function stopScheduler() {
        gmSet(KEY_SCHED_ON, false);
        gmSet(KEY_NEXT_RUN, 0);
        appendLog('INFO', '定时收菜已停止');
        if (window.__wodHarvestPanel) window.__wodHarvestPanel.refreshStatus();
    }

    // 每分钟检查是否到点（所有标签页都会跑，startHarvest 内有所有权互斥）
    setInterval(() => {
        if (!gmGet(KEY_SCHED_ON, false)) return;
        const next = gmGet(KEY_NEXT_RUN, 0);
        if (!next || Date.now() < next) return;
        const task = getTask();
        if (task && task.running) return; // 正在执行
        // 先把下次时间占位，降低多标签页同时触发的概率
        gmSet(KEY_NEXT_RUN, Date.now() + getIntervalMin() * 60 * 1000);
        startHarvest(true);
    }, 60000);

    // ============================================================
    // 页面加载入口：任务进行中则续跑
    // ============================================================

    function onPageLoaded() {
        const task = getTask();
        if (!task || !task.running) {
            // 收菜任务不在跑：检查是否有出售任务需要续跑
            onSellPageLoaded();
            return;
        }

        // 会话过期检测：任务进行中被踢到登录页则终止（不做自动登录）
        const info = loginFormInfo();
        if (info.hasForm || info.onLoginPage) {
            appendLog('ERROR', '会话已过期（跳转到登录页），任务终止。请手动登录后重新开始。');
            stopHarvest('登录已过期');
            return;
        }

        const owner = gmGet(KEY_OWNER, null);
        if (owner && owner.id !== TAB_ID && Date.now() - (owner.heartbeat || 0) < HEARTBEAT_STALE_MS) {
            return; // 其他标签页在执行
        }
        acquireOwnership();

        // 错误页检测（对应 ensure_page_valid）：刷新重试，上限 PAGE_RETRY_MAX 次
        if (isErrorPage()) {
            const n = (task.pageRetries || 0) + 1;
            if (n > PAGE_RETRY_MAX) {
                appendLog('ERROR', `连续 ${PAGE_RETRY_MAX} 次加载到错误页，任务终止。当前 URL: ${location.href}`);
                stopHarvest('页面持续加载失败');
                return;
            }
            task.pageRetries = n;
            setTask(task);
            appendLog('WARNING', `检测到错误页面，尝试刷新 (${n}/${PAGE_RETRY_MAX})... 当前: ${document.title || '(无标题)'}`);
            armLoadWatchdog(); // 刷新本身挂起时也能恢复
            setTimeout(() => location.reload(), 2000);
            return;
        }
        // 正常页面：清零错误页计数
        if (task.pageRetries) {
            task.pageRetries = 0;
            setTask(task);
        }

        // 看门狗强制恢复后的安全校验：落盘状态描述的页面（如"筛选完成
        // 待移动"）与实际页面（默认物品页，筛选已丢失）可能不一致，
        // 直接续跑会把整个背包误移进仓库
        if (task.recovered) validateAfterRecovery(task);

        appendLog('INFO', `页面就绪，继续步骤: ${task.step}${task.sub ? '/' + task.sub : ''}${task.cleanPhase ? '/clean:' + task.cleanPhase : ''}`);
        setTimeout(() => runNextStep(), EXTRA_WAIT_MS);
    }

    // 看门狗恢复后的状态校正：
    // - 卡在"切换英雄"：保留步骤、清子状态，重试点切换
    //   （英雄还没切走，重试安全）
    // - 卡在筛选/移动/清理：回当前英雄流程起点重做。
    //   各操作幂等（已移走的物品第二次全选时为空、自动跳过），
    //   宁可重做一遍，也不在筛选已失效的页面上全选移动
    function validateAfterRecovery(task) {
        task.recovered = false;
        if (task.step === 'next_hero') {
            task.sub = null;
            appendLog('WARNING', '恢复：重新尝试切换英雄');
        } else if (task.step === 'loop_begin' && task.sub === 'mentor_switching') {
            task.sub = null;
            appendLog('WARNING', '恢复：重新尝试跳过导师英雄');
        } else if (task.step !== 'goto_items' && task.step !== 'loop_begin') {
            task.step = 'loop_begin';
            task.sub = null;
            task.cleanPhase = null;
            task.cleanSub = null;
            task.cleanRound = 1;
            appendLog('WARNING', '恢复：回到当前英雄流程起点重做（页面筛选状态已在恢复中丢失）');
        }
        setTask(task);
    }

    // ============================================================
    // 浮动控制面板
    // ============================================================

    function buildPanel() {
        GM_addStyle(`
            #wod-harvest-panel {
                position: fixed; right: 12px; top: 12px; z-index: 99999;
                width: 310px; background: #1e1f26; color: #d8d9dd;
                border: 1px solid #3a3d47; border-radius: 10px;
                font: 12px/1.5 "Microsoft YaHei", Consolas, sans-serif;
                box-shadow: 0 4px 16px rgba(0,0,0,.4);
                user-select: none;
            }
            #wod-harvest-panel .wod-hp-head {
                display: flex; align-items: center; justify-content: space-between;
                padding: 8px 10px; cursor: move; background: #262833;
                border-radius: 10px 10px 0 0; font-weight: bold; font-size: 13px;
            }
            #wod-harvest-panel .wod-hp-head .dot {
                width: 9px; height: 9px; border-radius: 50%;
                display: inline-block; margin-right: 6px; background: #888;
            }
            #wod-harvest-panel .wod-hp-body { padding: 8px 10px; }
            #wod-harvest-panel .wod-hp-row { display: flex; gap: 6px; margin-bottom: 8px; align-items: center; }
            #wod-harvest-panel button {
                flex: 1; padding: 5px 0; border: none; border-radius: 6px; cursor: pointer;
                background: #3d63dd; color: #fff; font-size: 12px; white-space: nowrap;
            }
            #wod-harvest-panel button:hover { filter: brightness(1.15); }
            #wod-harvest-panel button.danger { background: #b3413f; }
            #wod-harvest-panel .wod-hp-status { font-size: 11px; color: #9a9da8; margin-bottom: 6px; }
            #wod-harvest-panel input[type=number] {
                width: 60px; background: #2a2c36; color: #d8d9dd; border: 1px solid #3a3d47;
                border-radius: 5px; padding: 4px 6px; font-size: 12px;
            }
            #wod-harvest-panel .wod-hp-log {
                height: 180px; overflow-y: auto; background: #14151a;
                border-radius: 6px; padding: 6px 8px; font: 11px/1.6 Consolas, monospace;
                white-space: pre-wrap; word-break: break-all; user-select: text;
            }
            #wod-harvest-panel .wod-hp-mini { color: #777; cursor: pointer; padding: 2px 8px; }
            #wod-harvest-panel .wod-hp-mini:hover { color: #ccc; }
        `);

        const panel = document.createElement('div');
        panel.id = 'wod-harvest-panel';

        // 标题栏
        const head = document.createElement('div');
        head.className = 'wod-hp-head';
        const title = document.createElement('span');
        title.style.display = 'flex';
        title.style.alignItems = 'center';
        const dot = document.createElement('i');
        dot.className = 'dot';
        title.appendChild(dot);
        title.appendChild(document.createTextNode(' WoD 自动收菜'));
        const mini = document.createElement('span');
        mini.className = 'wod-hp-mini';
        mini.textContent = '—';
        mini.title = '收起/展开';
        head.appendChild(title);
        head.appendChild(mini);

        const body = document.createElement('div');
        body.className = 'wod-hp-body';

        // 状态行
        const status = document.createElement('div');
        status.className = 'wod-hp-status';

        // 行1：开始 / 停止
        const row1 = document.createElement('div');
        row1.className = 'wod-hp-row';
        const btnStart = document.createElement('button');
        btnStart.textContent = '开始收菜';
        const btnStop = document.createElement('button');
        btnStop.textContent = '停止';
        btnStop.className = 'danger';
        row1.appendChild(btnStart);
        row1.appendChild(btnStop);

        // 行1.5：出售可卖物品（轮询所有英雄）
        const rowSell = document.createElement('div');
        rowSell.className = 'wod-hp-row';
        const btnSell = document.createElement('button');
        btnSell.textContent = `出售可卖物品（轮询，清单${SELLABLE_ITEMS.length}条）`;
        btnSell.title = '按内置可卖清单圈选物品并按NPC价出售，自动轮询所有英雄';
        rowSell.appendChild(btnSell);

        // 行2：定时开关 + 间隔
        const row2 = document.createElement('div');
        row2.className = 'wod-hp-row';
        const btnSched = document.createElement('button');
        btnSched.textContent = '启动定时';
        const lbl = document.createElement('span');
        lbl.textContent = '间隔';
        lbl.style.fontSize = '11px';
        const input = document.createElement('input');
        input.type = 'number';
        input.min = '1';
        input.value = getIntervalMin();
        input.title = '定时间隔（分钟）';
        const lblMin = document.createElement('span');
        lblMin.textContent = '分';
        lblMin.style.fontSize = '11px';
        row2.appendChild(btnSched);
        row2.appendChild(lbl);
        row2.appendChild(input);
        row2.appendChild(lblMin);

        // 行3：清空日志 / 隐藏面板
        const row3 = document.createElement('div');
        row3.className = 'wod-hp-row';
        const btnClear = document.createElement('button');
        btnClear.textContent = '清空日志';
        const btnHide = document.createElement('button');
        btnHide.textContent = '隐藏面板';
        row3.appendChild(btnClear);
        row3.appendChild(btnHide);

        // 日志区
        const logBox = document.createElement('div');
        logBox.className = 'wod-hp-log';

        body.appendChild(status);
        body.appendChild(row1);
        body.appendChild(rowSell);
        body.appendChild(row2);
        body.appendChild(row3);
        body.appendChild(logBox);
        panel.appendChild(head);
        panel.appendChild(body);
        document.body.appendChild(panel);

        // ----- 面板逻辑 -----
        function appendLogLine(line) {
            const atBottom = logBox.scrollTop + logBox.clientHeight >= logBox.scrollHeight - 24;
            const div = document.createElement('div');
            div.textContent = line;
            logBox.appendChild(div);
            while (logBox.childNodes.length > MAX_LOG) logBox.removeChild(logBox.firstChild);
            if (atBottom) logBox.scrollTop = logBox.scrollHeight;
        }

        function refreshStatus() {
            const task = getTask();
            const sellTask = getSellTask();
            const schedOn = gmGet(KEY_SCHED_ON, false);
            const next = gmGet(KEY_NEXT_RUN, 0);
            if (task && task.running) {
                dot.style.background = '#4caf50';
                status.textContent = `收菜中: ${task.step}${task.sub ? '/' + task.sub : ''}` +
                    (task.cleanPhase ? ` clean:${task.cleanPhase}` : '') +
                    ` | 已处理 ${task.processed.length} 英雄`;
            } else if (sellTask && sellTask.running) {
                dot.style.background = '#4caf50';
                status.textContent = `出售中: ${sellTask.step}${sellTask.sub ? '/' + sellTask.sub : ''}` +
                    ` | 已处理 ${sellTask.processed.length} 英雄 卖出 ${sellTask.totalSold} 件`;
            } else if (schedOn) {
                dot.style.background = '#e6a23c';
                status.textContent = next ? `定时待命，下次 ${formatTime(next)}` : '定时待命';
            } else {
                dot.style.background = '#888';
                status.textContent = '空闲';
            }
            btnSched.textContent = schedOn ? '停止定时' : '启动定时';
        }

        btnStart.addEventListener('click', () => {
            const v = parseFloat(input.value);
            if (!isNaN(v) && v > 0) gmSet(KEY_INTERVAL, v);
            startHarvest(false);
            refreshStatus();
        });

        btnSell.addEventListener('click', () => {
            startSell();
            refreshStatus();
        });

        btnStop.addEventListener('click', () => {
            // 收菜、出售哪个在跑停哪个
            const task = getTask();
            const sellTask = getSellTask();
            if (sellTask && sellTask.running) stopSell();
            else if (task && task.running) stopHarvest();
            else { stopHarvest(); stopSell(); }
            refreshStatus();
        });

        btnSched.addEventListener('click', () => {
            const v = parseFloat(input.value);
            if (isNaN(v) || v <= 0) {
                appendLog('WARNING', '无效的间隔时间');
                return;
            }
            gmSet(KEY_INTERVAL, v);
            if (gmGet(KEY_SCHED_ON, false)) {
                stopScheduler();
            } else {
                startScheduler();
            }
            refreshStatus();
        });

        btnClear.addEventListener('click', () => {
            gmSet(KEY_LOG, []);
            logBox.innerHTML = '';
        });

        btnHide.addEventListener('click', () => {
            gmSet(KEY_PANEL_HIDDEN, true);
            panel.style.display = 'none';
        });

        // 恢复上次收起/展开状态（跨页面保持）
        if (gmGet(KEY_PANEL_COLLAPSED, false)) {
            body.style.display = 'none';
            mini.textContent = '+';
        }

        mini.addEventListener('click', () => {
            const collapsed = body.style.display === 'none';
            body.style.display = collapsed ? '' : 'none';
            mini.textContent = collapsed ? '—' : '+';
            gmSet(KEY_PANEL_COLLAPSED, !collapsed);
        });

        // 拖动
        let dragging = false, offX = 0, offY = 0;
        head.addEventListener('mousedown', (e) => {
            if (e.target === mini || mini.contains(e.target)) return;
            dragging = true;
            offX = e.clientX - panel.offsetLeft;
            offY = e.clientY - panel.offsetTop;
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            panel.style.left = (e.clientX - offX) + 'px';
            panel.style.top = (e.clientY - offY) + 'px';
            panel.style.right = 'auto';
        });
        document.addEventListener('mouseup', () => { dragging = false; });

        // 载入历史日志
        (gmGet(KEY_LOG, [])).forEach(l => appendLogLine(l));

        window.__wodHarvestPanel = { appendLog: appendLogLine, refreshStatus };
        refreshStatus();
        setInterval(refreshStatus, 5000);
    }

    // ============================================================
    // 脚本菜单
    // ============================================================
    GM_registerMenuCommand('显示/隐藏 收菜面板', () => {
        const panel = document.getElementById('wod-harvest-panel');
        if (panel) {
            const hidden = panel.style.display === 'none';
            gmSet(KEY_PANEL_HIDDEN, !hidden);
            panel.style.display = hidden ? '' : 'none';
        } else {
            gmSet(KEY_PANEL_HIDDEN, false);
            buildPanel();
        }
    });
    GM_registerMenuCommand('停止当前任务', () => {
        const task = getTask();
        const sellTask = getSellTask();
        if (sellTask && sellTask.running) stopSell('手动停止（菜单）');
        else if (task && task.running) stopHarvest('手动停止（菜单）');
        else { stopHarvest('手动停止（菜单）'); stopSell('手动停止（菜单）'); }
    });

    // ============================================================
    // 启动
    // ============================================================
    function main() {
        if (!location.hostname.includes('world-of-dungeons')) return;

        // 已登录的游戏页面才建面板（登录页/首页不建，但任务续跑检测仍执行）
        const info = loginFormInfo();
        const path = location.pathname.replace(/\/+$/, '');
        const isGamePage = !info.hasForm && !info.onLoginPage && path !== '' && path !== '/wod';

        if (isGamePage && !gmGet(KEY_PANEL_HIDDEN, false)) {
            buildPanel();
        }

        onPageLoaded();
    }

    main();
})();

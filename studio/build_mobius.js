/**
 * 莫比乌斯环概念地图构建引擎 v2.0 (JS)
 * 从 Python build_mobius.py 移植
 */
(function () {
  'use strict';

  // 默认五空配置
  var DEFAULT_EMPTINESS = {
    sunyata: true, mirror: true, breath: true, wane: true, ascend: true,
    mirrorRatio: 0.42, breathPeriod: 10000, breathAmplitude: 15,
    fadeStart: 35000, fadeEnd: 50000, fadeTarget: 0.15, fadeRestore: 0.5,
    ascendRatio: 0.2
  };

  /**
   * 转义字符串用于 JS 单引号
   */
  function escJs(s) {
    return s.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n');
  }

  /**
   * 单个概念 → JS 对象字符串
   */
  function conceptToJs(c) {
    var docsStr = JSON.stringify(c.docs || [], undefined, 0);
    var line = "{ label: '" + escJs(c.label) + "', desc: '" + escJs(c.desc || '') + "', docs: " + docsStr + " }";
    if (c.wuxing) {
      line = line.slice(0, -2) + ", wuxing:'" + escJs(c.wuxing) + "' }";
    }
    if (c.bagua) {
      line = line.slice(0, -2) + ", bagua:'" + escJs(c.bagua) + "' }";
    }
    return line;
  }

  /**
   * 整个 rings 数据 → JS 字符串
   */
  function buildRingsJs(rings) {
    var lines = ['var DEFAULT_RINGS = ['];
    for (var ri = 0; ri < rings.length; ri++) {
      var r = rings[ri];
      lines.push('    {');
      lines.push("      label: '" + escJs(r.label) + "', R: " + (r.R || 150) + ", w: " + (r.w || 25) + ", yOffset: " + (r.yOffset || 0) + ", color: '" + (r.color || '#4ECDC4') + "',");
      lines.push('      concepts: [');
      var concepts = r.concepts || [];
      for (var ci = 0; ci < concepts.length; ci++) {
        lines.push('        ' + conceptToJs(concepts[ci]) + ',');
      }
      lines.push('      ]');
      lines.push('    }' + (ri < rings.length - 1 ? ',' : ''));
    }
    lines.push('  ];');
    return lines.join('\n');
  }

  /**
   * EMPTINESS 配置 → JS 字符串
   */
  function buildEmptinessJs(emp) {
    var lines = ['  var EMPTINESS = {'];
    var keys = Object.keys(emp);
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      var v = emp[k];
      if (typeof v === 'boolean') {
        lines.push('    ' + k + ': ' + (v ? 'true' : 'false'));
      } else if (typeof v === 'number') {
        lines.push('    ' + k + ': ' + v);
      } else {
        lines.push("    " + k + ": '" + escJs(String(v)) + "'");
      }
      if (i < keys.length - 1) {
        lines[lines.length - 1] += ',';
      }
    }
    lines.push('  };');
    return lines.join('\n');
  }

  /**
   * djb2 字符串哈希函数
   */
  function djb2(str) {
    var hash = 5381;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash) + str.charCodeAt(i);
    }
    return Math.abs(hash).toString(16).substring(0, 8);
  }

  /**
   * 生成 localStorage 的 key
   */
  function generateStorageKey(title) {
    return 'mobius_' + djb2(title);
  }

  /**
   * 主构建函数
   * @param {string} templateHtml - template.html 的完整内容
   * @param {object} data - JSON 数据（包含 rings 数组）
   * @param {string} title - 页面标题
   * @param {object} emptinessConfig - 可选，自定义 emptiness 配置
   * @returns {string} 完整的 HTML 字符串
   */
  function build(templateHtml, data, title, emptinessConfig) {
    title = title || '概念地图';
    var html = templateHtml;

    // 提取 rings
    var rings = data.rings || (Array.isArray(data) ? data : []);

    // 1. 替换 DEFAULT_RINGS
    var oldStart = 'var DEFAULT_RINGS = [';
    var oldEnd = '  ];';
    var si = html.indexOf(oldStart);
    var ei = html.indexOf(oldEnd, si) + oldEnd.length;
    html = html.substring(0, si) + buildRingsJs(rings) + html.substring(ei);

    // 2. 构建 emptiness 配置
    var emp;
    if (emptinessConfig) {
      // 使用用户自定义配置（合并默认值）
      emp = {};
      for (var k in DEFAULT_EMPTINESS) {
        if (DEFAULT_EMPTINESS.hasOwnProperty(k)) {
          emp[k] = DEFAULT_EMPTINESS[k];
        }
      }
      if (typeof emptinessConfig === 'object') {
        for (var ck in emptinessConfig) {
          if (emptinessConfig.hasOwnProperty(ck)) {
            emp[ck] = emptinessConfig[ck];
          }
        }
      }
    } else if (typeof data === 'object' && !Array.isArray(data) && data.emptiness) {
      emp = {};
      for (var dk in DEFAULT_EMPTINESS) {
        if (DEFAULT_EMPTINESS.hasOwnProperty(dk)) {
          emp[dk] = DEFAULT_EMPTINESS[dk];
        }
      }
      for (var ek in data.emptiness) {
        if (data.emptiness.hasOwnProperty(ek)) {
          emp[ek] = data.emptiness[ek];
        }
      }
    } else {
      emp = {};
      for (var fk in DEFAULT_EMPTINESS) {
        if (DEFAULT_EMPTINESS.hasOwnProperty(fk)) {
          emp[fk] = DEFAULT_EMPTINESS[fk];
        }
      }
    }

    // 替换 EMPTINESS 配置
    var empOld = '  var EMPTINESS = {';
    var empSi = html.indexOf(empOld);
    var braceCount = 0;
    var empEi = empSi;
    for (var j = empSi; j < html.length; j++) {
      if (html[j] === '{') braceCount++;
      else if (html[j] === '}') {
        braceCount--;
        if (braceCount === 0) {
          empEi = j + 2; // 包含 };\n
          break;
        }
      }
    }
    html = html.substring(0, empSi) + buildEmptinessJs(emp) + html.substring(empEi);

    // 3. 替换三个标题
    html = html.replace('唯识论 \u00b7 种子现行 \u00b7 v1.2 修正版', title);
    html = html.replace('唯识论 \u00b7 种子现行 \u00b7 概念地图', title);
    html = html.replace('莫比乌斯环概念地图 \u00b7 v2.0', title);

    // 4. 替换 Legend 三层标注
    var legendLines = [];
    for (var li = 0; li < rings.length; li++) {
      var ring = rings[li];
      var label = ring.label || '未命名';
      var color = ring.color || '#4ECDC4';
      var firstConcept = (ring.concepts && ring.concepts[0]) ? ring.concepts[0].label : '';
      var desc = firstConcept ? ' \u00b7 ' + firstConcept : '';
      legendLines.push('<div><span class="dot" style="background:' + color + '"></span>' + label + desc + '</div>');
    }
    html = html.replace('<!--LEGEND_RINGS-->', legendLines.join('\n'));

    // 5. 替换 STORAGE_KEY
    var storageKey = generateStorageKey(title);
    html = html.replace("var STORAGE_KEY = 'weishi_mobius_data'", "var STORAGE_KEY = '" + storageKey + "'");

    return html;
  }

  // 导出为全局对象
  window.MobiusBuilder = {
    build: build,
    generateStorageKey: generateStorageKey,
    DEFAULT_EMPTINESS: DEFAULT_EMPTINESS
  };

})();

/* ============================================================
   供应商管理系统 — 全局交互脚本
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {

  /* ---- 移动端侧边栏切换 ---- */
  var menuBtn = document.getElementById("mobileMenuBtn");
  var sidebar = document.getElementById("sidebar");
  if (menuBtn && sidebar) {
    menuBtn.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
    document.querySelector(".main-wrapper").addEventListener("click", function () {
      if (sidebar.classList.contains("open")) {
        sidebar.classList.remove("open");
      }
    });
  }

  /* ---- 已打开页面标签 ---- */
  initSubpageTabs();

  /* ---- 删除确认 ---- */
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      var msg = this.getAttribute("data-confirm") || "确定要执行此操作吗？";
      if (!confirm(msg)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  /* ---- 表单提交防重复点击 ---- */
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) {
        submitBtn.disabled = true;
      }
    });
  });

  /* ---- Flash 消息自动消失 ---- */
  setTimeout(function () {
    document.querySelectorAll(".flash-messages .alert").forEach(function (alert) {
      alert.style.transition = "opacity 0.5s";
      alert.style.opacity = "0";
      setTimeout(function () { alert.remove(); }, 500);
    });
  }, 4000);

  /* ---- 图片点击放大 ---- */
  document.querySelectorAll("[data-image-full]").forEach(function (img) {
    img.addEventListener("click", function () {
      var overlay = document.createElement("div");
      overlay.className = "image-modal-overlay";
      var fullImg = document.createElement("img");
      fullImg.src = this.getAttribute("data-image-full");
      overlay.appendChild(fullImg);
      document.body.appendChild(overlay);
      overlay.addEventListener("click", function () { overlay.remove(); });
    });
  });

  /* ---- 文件上传预览 ---- */
  var uploadInputs = document.querySelectorAll("[data-upload-preview]");
  uploadInputs.forEach(function (input) {
    var previewContainer = document.getElementById(input.getAttribute("data-upload-preview"));
    if (!previewContainer) return;

    var dropZone = previewContainer.querySelector(".upload-zone");
    if (dropZone) {
      ["dragenter", "dragover"].forEach(function (evt) {
        dropZone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropZone.classList.add("dragover");
        });
      });
      ["dragleave", "drop"].forEach(function (evt) {
        dropZone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropZone.classList.remove("dragover");
        });
      });
      dropZone.addEventListener("drop", function (e) {
        input.files = e.dataTransfer.files;
        showUploadPreviews(input, previewContainer);
      });
    }

    input.addEventListener("change", function () {
      showUploadPreviews(input, previewContainer);
    });
  });

  function initSubpageTabs() {
    var tabBar = document.getElementById("subpageTabs");
    var pageTitle = document.querySelector(".page-title");
    if (!tabBar || !pageTitle) return;

    var storageKey = "scm.openSubpageTabs";
    var maxTabs = 12;
    var currentUrl = window.location.pathname + window.location.search;
    var currentTitle = normalizeTabTitle(pageTitle.textContent || document.title || "当前页面");
    var activeMenu = tabBar.getAttribute("data-active-menu") || "dashboard";
    var dashboardUrl = tabBar.getAttribute("data-dashboard-url") || "/";
    var moduleUrls = [
      tabBar.getAttribute("data-dashboard-url"),
      tabBar.getAttribute("data-orders-url"),
      tabBar.getAttribute("data-booking-url"),
      tabBar.getAttribute("data-container-url"),
      tabBar.getAttribute("data-sku-url")
    ].filter(Boolean);
    var isModuleHome = moduleUrls.indexOf(currentUrl) !== -1;

    var tabs = readTabs(storageKey).filter(function (tab) {
      return tab && tab.url && tab.title && moduleUrls.indexOf(tab.url) === -1;
    });
    var existingIndex = tabs.findIndex(function (tab) {
      return tab.url === currentUrl;
    });
    var currentTab = {
      title: currentTitle,
      url: currentUrl,
      menu: activeMenu,
      updatedAt: Date.now()
    };

    if (isModuleHome) {
      if (existingIndex >= 0) {
        tabs.splice(existingIndex, 1);
      }
    } else if (existingIndex >= 0) {
      tabs[existingIndex] = currentTab;
    } else {
      tabs.push(currentTab);
    }
    if (tabs.length > maxTabs) {
      tabs = tabs.slice(tabs.length - maxTabs);
    }
    writeTabs(storageKey, tabs);
    renderTabs(tabBar, tabs, currentUrl);

    tabBar.addEventListener("click", function (event) {
      var closeAllBtn = event.target.closest(".subpage-tabs-close-all");
      if (closeAllBtn) {
        event.preventDefault();
        event.stopPropagation();
        writeTabs(storageKey, []);
        if (window.location.pathname + window.location.search === dashboardUrl) {
          renderTabs(tabBar, [], currentUrl);
        } else {
          window.location.href = dashboardUrl;
        }
        return;
      }

      var closeBtn = event.target.closest(".subpage-tab-close");
      if (!closeBtn) return;

      event.preventDefault();
      event.stopPropagation();

      var closeUrl = closeBtn.getAttribute("data-tab-url");
      var nextTabs = readTabs(storageKey).filter(function (tab) {
        return tab.url !== closeUrl;
      });
      writeTabs(storageKey, nextTabs);

      if (closeUrl === currentUrl) {
        var nextTab = nextTabs[nextTabs.length - 1];
        window.location.href = nextTab ? nextTab.url : dashboardUrl;
        return;
      }

      renderTabs(tabBar, nextTabs, currentUrl);
    });
  }

  function normalizeTabTitle(title) {
    return title.replace(/\s+/g, " ").trim() || "当前页面";
  }

  function readTabs(storageKey) {
    try {
      var value = window.localStorage.getItem(storageKey);
      return value ? JSON.parse(value) : [];
    } catch (err) {
      return [];
    }
  }

  function writeTabs(storageKey, tabs) {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(tabs));
    } catch (err) {
      // localStorage 不可用时仍保留当前页面基本渲染。
    }
  }

  function renderTabs(tabBar, tabs, currentUrl) {
    tabBar.innerHTML = "";
    tabs.forEach(function (tab) {
      var item = document.createElement("div");
      item.className = "subpage-tab" + (tab.url === currentUrl ? " active" : "");

      var link = document.createElement("a");
      link.className = "subpage-tab-link";
      link.href = tab.url;
      link.title = tab.title;
      link.textContent = tab.title;

      var close = document.createElement("button");
      close.className = "subpage-tab-close";
      close.type = "button";
      close.setAttribute("aria-label", "关闭 " + tab.title);
      close.setAttribute("data-tab-url", tab.url);
      close.textContent = "×";

      item.appendChild(link);
      item.appendChild(close);
      tabBar.appendChild(item);
    });

    if (tabs.length > 0) {
      var closeAll = document.createElement("button");
      closeAll.className = "subpage-tabs-close-all";
      closeAll.type = "button";
      closeAll.setAttribute("aria-label", "关闭所有页面");
      closeAll.title = "关闭所有页面";
      closeAll.textContent = "关闭全部";
      tabBar.appendChild(closeAll);
    }
  }

  function showUploadPreviews(input, container) {
    var fileCount = container.querySelector(".upload-file-count");
    if (fileCount) {
      fileCount.textContent = input.files.length + " 个文件已选择";
    }

    var previewList = container.querySelector(".upload-preview-list");
    if (!previewList) return;
    previewList.innerHTML = "";

    Array.from(input.files).forEach(function (file) {
      if (!file.type.startsWith("image/")) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        var item = document.createElement("div");
        item.className = "preview-item";
        var img = document.createElement("img");
        img.src = e.target.result;
        item.appendChild(img);
        previewList.appendChild(item);
      };
      reader.readAsDataURL(file);
    });
  }
});

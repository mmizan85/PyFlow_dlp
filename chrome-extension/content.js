// PyFlow Content Script v3.0 — Universal Video Detector
// Detects downloadable media from any yt-dlp compatible site
"use strict";

(function () {

  // ── yt-dlp supported site patterns ──────────────────────────────────────
  // These cover the major extractors built into yt-dlp
  const YTDLP_SITES = [
    // Video platforms
    { host: /youtube\.com|youtu\.be/,        name: "YouTube",     color: "#ff0000" },
    { host: /vimeo\.com/,                    name: "Vimeo",       color: "#1ab7ea" },
    { host: /twitch\.tv/,                    name: "Twitch",      color: "#9146ff" },
    { host: /dailymotion\.com/,              name: "Dailymotion", color: "#0066dc" },
    { host: /bilibili\.com/,                 name: "Bilibili",    color: "#fb7299" },
    { host: /nicovideo\.jp/,                 name: "NicoVideo",   color: "#333" },
    { host: /rumble\.com/,                   name: "Rumble",      color: "#85c742" },
    { host: /odysee\.com|lbry\.tv/,          name: "Odysee",      color: "#ef1970" },
    { host: /peertube\.|framatube\.org/,     name: "PeerTube",    color: "#f1680d" },
    { host: /brightcove\.com/,               name: "Brightcove",  color: "#ff6600" },
    { host: /wistia\.com|wistia\.net/,       name: "Wistia",      color: "#54bbff" },
    { host: /kaltura\.com/,                  name: "Kaltura",     color: "#007cbe" },
    { host: /ted\.com/,                      name: "TED",         color: "#e62b1e" },
    { host: /aparat\.com/,                   name: "Aparat",      color: "#ee2121" },
    { host: /streamable\.com/,               name: "Streamable",  color: "#3d3d3d" },
    { host: /gfycat\.com/,                   name: "Gfycat",      color: "#2d9de0" },
    { host: /imgur\.com/,                    name: "Imgur",       color: "#1bb76e" },
    { host: /liveleak\.com/,                 name: "LiveLeak",    color: "#ff0000" },
    { host: /metacafe\.com/,                 name: "Metacafe",    color: "#ff6600" },
    { host: /ok\.ru/,                        name: "OK.ru",       color: "#f7931d" },
    { host: /mail\.ru/,                      name: "Mail.ru",     color: "#005ff9" },
    { host: /vk\.com/,                       name: "VKontakte",   color: "#4a76a8" },
    { host: /coub\.com/,                     name: "Coub",        color: "#22a5e5" },
    { host: /mixcloud\.com/,                 name: "Mixcloud",    color: "#5000ff" },
    { host: /audiomack\.com/,                name: "Audiomack",   color: "#f4932e" },
    // Social media
    { host: /twitter\.com|x\.com/,          name: "X / Twitter", color: "#1da1f2" },
    { host: /instagram\.com/,               name: "Instagram",   color: "#c13584" },
    { host: /facebook\.com|fb\.com/,        name: "Facebook",    color: "#1877f2" },
    { host: /tiktok\.com/,                  name: "TikTok",      color: "#ff0050" },
    { host: /reddit\.com/,                  name: "Reddit",      color: "#ff4500" },
    { host: /pinterest\.com/,              name: "Pinterest",   color: "#e60023" },
    { host: /snapchat\.com/,               name: "Snapchat",    color: "#fffc00" },
    { host: /linkedin\.com/,               name: "LinkedIn",    color: "#0077b5" },
    // Music & Podcasts
    { host: /soundcloud\.com/,             name: "SoundCloud",  color: "#ff5500" },
    { host: /bandcamp\.com/,               name: "Bandcamp",    color: "#1da0c3" },
    { host: /spotify\.com/,               name: "Spotify",     color: "#1db954" },
    { host: /mixlr\.com/,                  name: "Mixlr",       color: "#3799bb" },
    { host: /podbean\.com/,               name: "Podbean",     color: "#f16421" },
    // News & Media
    { host: /bbc\.co\.uk|bbc\.com/,       name: "BBC",         color: "#bb1919" },
    { host: /cnn\.com/,                    name: "CNN",         color: "#cc0000" },
    { host: /nytimes\.com/,               name: "NYTimes",     color: "#333" },
    { host: /washingtonpost\.com/,        name: "WashPost",    color: "#231f20" },
    { host: /theguardian\.com/,           name: "Guardian",    color: "#052962" },
    { host: /reuters\.com/,               name: "Reuters",     color: "#f58220" },
    { host: /bloomberg\.com/,             name: "Bloomberg",   color: "#1769b4" },
    // Streaming
    { host: /twitch\.tv/,                  name: "Twitch",      color: "#9146ff" },
    { host: /afreecatv\.com/,             name: "AfreecaTV",   color: "#006be6" },
    { host: /abematv\.abema\.io/,         name: "AbemaTV",     color: "#00b9e9" },
    // Adult (filtered, domain only for detection)
    { host: /pornhub\.com/,               name: "PornHub",     color: "#f90" },
    { host: /xvideos\.com/,               name: "XVideos",     color: "#e74c3c" },
    // Generic — catch anything with og:video or HTML5 <video>
    { host: /.*/,                          name: "Web Video",   color: "#00d4ff" },
  ];

  // ── State ────────────────────────────────────────────────────────────────
  let injected = false;
  let lastUrl  = location.href;

  // ── URL-change watcher (handles SPAs) ────────────────────────────────────
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl   = location.href;
      injected  = false;
      setTimeout(tryInject, 1000);
    }
  }).observe(document.documentElement, { childList: true, subtree: true });

  // ── Message listener — popup asks for page info ───────────────────────────
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === "GET_PAGE_INFO") {
      sendResponse(buildPageInfo());
      return true;
    }
  });

  // ── Build page information object ────────────────────────────────────────
  function buildPageInfo() {
    const url    = location.href;
    const host   = location.hostname.replace(/^www\./, "");
    const site   = detectSite(host);

    // YouTube specifics
    const isYT      = /youtube\.com|youtu\.be/.test(host);
    const params    = new URLSearchParams(location.search);
    const videoId   = isYT ? params.get("v") : null;
    const isPlaylist = isYT && params.has("list");

    // Title — og:title first, then page title
    const ogTitle   = document.querySelector('meta[property="og:title"]')?.content;
    const title     = (ogTitle || document.title || "Untitled").replace(/ ?[-|–] ?YouTube$/, "").trim();

    // Thumbnail
    const ogImage   = document.querySelector('meta[property="og:image"]')?.content;
    const thumbnail = videoId
      ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`
      : ogImage || null;

    // Try to detect direct video URL from og:video or <video src>
    const ogVideo  = document.querySelector('meta[property="og:video:url"], meta[property="og:video"]')?.content;
    const videoEl  = document.querySelector("video[src]")?.src;
    const directVideoUrl = ogVideo || videoEl || null;

    // Duration from og:video:duration or yt
    const duration  = document.querySelector('meta[property="og:video:duration"]')?.content || null;

    // Check if there's actually detectable media on this page
    const hasMedia = isYT
      ? !!params.get("v")
      : !!(ogVideo || videoEl || detectMediaInPage());

    return {
      url, host, title, thumbnail,
      siteName: site.name,
      siteColor: site.color,
      isYouTube: isYT,
      isPlaylist,
      videoId,
      directVideoUrl,
      duration,
      hasMedia,
      isSupported: site !== null,
    };
  }

  function detectSite(host) {
    for (const s of YTDLP_SITES) {
      if (s.host.test(host)) return s;
    }
    return { name: "Web", color: "#888" };
  }

  function detectMediaInPage() {
    // Check for <video> or <audio> tags, or common embed patterns
    return !!(
      document.querySelector("video, audio") ||
      document.querySelector('iframe[src*="youtube"], iframe[src*="vimeo"], iframe[src*="twitch"]') ||
      document.querySelector('[data-video-id], [data-media-id]')
    );
  }

  // ── Button injection ──────────────────────────────────────────────────────
  function tryInject() {
    if (injected) return;
    const info = buildPageInfo();
    if (!info.hasMedia && !info.isYouTube) return;

    const bar = findActionBar(info.isYouTube);
    if (!bar) { setTimeout(tryInject, 800); return; }

    createAndInjectButton(bar, info);
  }

  function findActionBar(isYT) {
    if (isYT) {
      const selectors = [
        "#top-level-buttons-computed",
        "#top-level-buttons",
        "ytd-menu-renderer #top-level-buttons-computed",
      ];
      for (const s of selectors) {
        const el = document.querySelector(s);
        if (el) return el;
      }
    }
    // Generic fallbacks
    for (const s of [
      '[data-testid="share-button"]',
      ".share-button", ".action-buttons", ".video-actions",
    ]) {
      const el = document.querySelector(s);
      if (el?.parentElement) return el.parentElement;
    }
    return null;
  }

  function createAndInjectButton(bar, info) {
    if (document.getElementById("pyflow-inject-btn")) return;

    const btn = document.createElement("button");
    btn.id = "pyflow-inject-btn";
    btn.className = "pyflow-inject-btn";
    btn.title = "Download with PyFlow";
    btn.innerHTML = `
      <svg class="pyflow-dl-icon" viewBox="0 0 20 20" fill="none">
        <path d="M10 2v10M6 8l4 4 4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M3 14v1a2 2 0 002 2h10a2 2 0 002-2v-1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
      <span>PyFlow</span>`;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      showFloatingNotice(info);
    });

    bar.insertBefore(btn, bar.firstChild);
    injected = true;
  }

  // ── Floating notice ───────────────────────────────────────────────────────
  function showFloatingNotice(info) {
    document.getElementById("pyflow-notice")?.remove();

    const notice = document.createElement("div");
    notice.id = "pyflow-notice";
    notice.className = "pyflow-notice";
    notice.innerHTML = `
      <div class="pfn-glow"></div>
      <div class="pfn-body">
        <div class="pfn-header">
          <span class="pfn-logo">⬇ PyFlow</span>
          <button class="pfn-close" id="pfnClose">✕</button>
        </div>
        <p class="pfn-msg">Click the <strong>PyFlow icon</strong> in your browser toolbar to download from <strong>${escHtml(info.siteName)}</strong>.</p>
        <div class="pfn-site">
          <span class="pfn-dot" style="background:${info.siteColor}"></span>
          <span>${escHtml(info.siteName)} detected</span>
        </div>
      </div>`;

    document.body.appendChild(notice);
    requestAnimationFrame(() => notice.classList.add("pfn-show"));

    document.getElementById("pfnClose").onclick = dismissNotice;
    setTimeout(dismissNotice, 6000);
  }

  function dismissNotice() {
    const n = document.getElementById("pyflow-notice");
    if (n) { n.classList.remove("pfn-show"); setTimeout(() => n.remove(), 350); }
  }

  function escHtml(s) {
    return (s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryInject);
  } else {
    setTimeout(tryInject, 600);
  }

})();

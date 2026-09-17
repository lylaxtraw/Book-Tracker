# Installing on Mobile Devices

Bookmark is a **Progressive Web App (PWA)**, which means it works like a native app on your phone without needing to go to an app store. It's fast, lightweight, and works offline!

## Quick Start

### iOS (iPhone or iPad)

1. Open **Safari** (not Chrome)
2. Navigate to your Boocker instance (e.g., `https://boocker.fly.dev`)
3. Tap the **Share button** at the bottom (looks like a square with an arrow)
4. Scroll down and tap **"Add to Home Screen"**
5. Choose a name (default is fine)
6. Tap **"Add"** in the top-right corner
7. Done! The app now appears on your home screen

**Note:** Use Safari for best results on iOS. Chrome and other browsers on iOS have limitations for adding PWAs to the home screen.

### Android (Phone or Tablet)

1. Open **Chrome** or **Microsoft Edge** 
2. Navigate to your Bookmark instance
3. Tap the **menu button** (three vertical dots) in the top-right corner
4. Look for **"Install app"** or **"Create shortcut"**
   - The exact wording depends on your browser and Android version
5. Confirm the installation
6. The app will appear on your home screen immediately

**Note:** Android 8+ recommended. Some older devices may show "Create shortcut" instead of "Install app".

### Desktop (Windows, Mac, or Linux)

1. Open **Chrome**, **Edge**, **Brave**, or **Opera** browser
2. Navigate to your Bookmark instance
3. Look for an **install button** in the address bar
   - It usually looks like a small box with an arrow or a plus sign
   - On some browsers, it's in the menu (three dots) → "Install"
4. Confirm the installation
5. The app opens in its own window (no browser chrome)

**Note:** Does NOT work in Safari on Mac. Firefox doesn't support PWA installation.

---

## What You Get

### When Installed

✅ **App-like Experience**
- Dedicated app window (looks like a native app)
- Appears in app switcher
- Can pin to taskbar or dock
- No browser address bar or tabs

✅ **Offline Support**
- Read your existing library offline
- Changes queue up and sync when you're back online
- Service worker caches the app shell and recent data

✅ **Fast Performance**
- Instant launch (no browser startup time)
- Smooth animations and transitions
- Responsive to touch

✅ **Data Privacy**
- All data stays on your server
- No cloud syncing unless you set it up
- You control where your library lives

### Limitations

⚠️ **No App Store Updates**
- Updates happen automatically when you open the app online
- Manually check for updates via "Check app updates" in Settings

⚠️ **No Push Notifications** (yet)
- Feature is in development
- You'll see it in Settings when ready

⚠️ **Device-Specific**
- Each device has its own "installation"
- Installing on phone, tablet, and desktop are separate actions
- Data syncs across devices via your server

---

## Troubleshooting

### "Install app" option doesn't appear

**Android:**
- Make sure you're using Chrome, Edge, or Brave (not Samsung Internet or Firefox)
- Try reloading the page (`Ctrl+Shift+R`)
- Some devices require Android 8+
- Check that HTTPS is enabled on your server

**iOS:**
- Use Safari, not Chrome
- Make sure the device has at least 50MB free space
- Try reloading the page in Safari

**Desktop:**
- Use a Chromium-based browser (Chrome, Edge, Brave, Opera)
- Firefox and Safari don't support PWA installation
- Reload the page if the install prompt doesn't appear

### App won't sync changes offline

- This is expected behavior
- Changes will sync once you're back online
- Check your connection and reload if changes don't sync after 10 seconds

### How do I update the app?

- PWA updates happen automatically in the background
- The next time you open the app, it checks for updates
- For manual updates: Close the app completely, reopen it, and allow it to check

### How do I uninstall?

**iOS:**
- Long-press the app icon on home screen
- Tap "Remove" → "Remove from Home Screen"

**Android:**
- Long-press the app icon
- Tap "Uninstall" (if it appears) or go to Settings → Apps and uninstall from there

**Desktop:**
- Chrome: Menu → "More tools" → "App shortcuts" → right-click app → "Remove"
- Edge: Settings → Apps → find the app → "Uninstall"

---

## Tips & Best Practices

💡 **Mobile-First Design**
- Bookmark is designed mobile-first, so it's perfect on phones
- Use portrait mode (works great in both)
- The interface adapts to any screen size

💡 **Battery Life**
- Bookmark is lightweight and uses minimal battery
- Syncing only happens when you interact with the app
- No background notifications draining your battery

💡 **Data Usage**
- The first load downloads ~50KB of app code
- Book covers and data sync only as needed
- Subsequent loads use cached data (very fast, no data usage)

💡 **Multiple Devices**
- Install on phone, tablet, and desktop
- All changes sync automatically via your server
- Latest changes always visible on all devices

---

## Frequently Asked Questions

**Q: Is this a real app or just a website?**
A: It's a Progressive Web App (PWA) — a modern web app that behaves like a native app. It works offline, has an app icon, and feels just like a native app, but is built with web technologies.

**Q: Will it work offline?**
A: Yes! The app caches your library so you can browse it offline. Changes sync automatically when you're back online.

**Q: Can I have it on multiple devices?**
A: Absolutely! Install on as many devices as you want. All changes sync through your server.

**Q: Is my data safe?**
A: Yes. If you're self-hosting, all data stays on your server. If using the public instance, that data is only accessible to you with your password.

**Q: How much storage does it use?**
A: Very little — typically less than 10MB including cached data. Much lighter than a traditional app.

**Q: Can I remove the bookmark from my library?**
A: Yes, uninstall it like any app on your device. Uninstalling removes the shortcut only; your data stays on the server.

---

For more help, see the [main README](../README.md) or [documentation](./index.md).

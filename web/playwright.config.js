import {defineConfig} from '@playwright/test';

export default defineConfig({
  testDir:'./e2e',
  projects:[{name:'desktop',use:{viewport:{width:1280,height:720}}},{name:'mobile',use:{viewport:{width:390,height:844}}}],
  use:{baseURL:process.env.STOCK_UI_BASE_URL || 'http://127.0.0.1:5178', headless:true, channel:process.env.STOCK_UI_BROWSER_CHANNEL},
  webServer:process.env.STOCK_UI_EXTERNAL_SERVER ? undefined : {command:'npm run dev -- --port 5178 --configLoader runner', url:'http://127.0.0.1:5178', reuseExistingServer:true},
});

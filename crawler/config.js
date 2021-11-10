// symlinked to node_crawler/config.js
// ln -s .../crawler/config.js .../node_crawler/config.js
const parser = require('../../node-crawler/parser'); // this is relative to file position
const result = require('dotenv').config({ path: '../main/.env'}); // this is relative to script start position

// modules which will always be loaded
const modules = ['frames'];
//const modules = [];


// crawl settings
const url_count = 10; // how many urls before a browser gets restarted
const maxUrls = 100;  // max urls per crawled site: for the collectLinks module and new also for frames; 100?
const sameSite = true; // the crawler has to stay on the sameSite (not origin)
const url_retries = 2; // crawler tries N times if new jobs/sites are available before quitting 
const crawl_retries = 3; // how ofter the crawler retries when there was an error
const collectUrlsWhileCrawling = true; // if this is set the crawler "crawls" and visits additional URLs (only looks at <a> tags)
const depth = 3; // max depth for the collectLinks module, and new also for frames

const clearProfileOnShutdown = false;
// Delimiter for the URLs CSV file can be overwritten via dynamic option
const csvDelimiter = ',';

// timings
const load_timeout = 20000;  // 20s max loading time
const execution_time_after_load = 5000; // 5s max execution time
const module_timeout = 5000;  // 5s max module time

// when crawler considers navigation (load) to be successful
const waitUntil = "load";   // one of load, domcontentloaded, networkidle0, networkidle2
// see: https://pptr.dev/#?product=Puppeteer&version=v10.2.0&show=api-pagewaitfornavigationoptions

// DB stuff
const db_user = process.env.DB_USER;
const db_host = process.env.DB_HOST;
const db_port = process.env.DB_PORT;
const db_pass = process.env.DB_PASSWORD;
const db_engine = 'postgres';
const db_name = process.env.DB_NAME;
const shardPath = '/data/scripts';

const DEFAULT_FLAGS = [
    // Disable built-in Google Translate service
    '--disable-translate',
    // Disable all chrome extensions entirely
    '--disable-extensions',
    // Disable various background network services, including extension updating,
    //   safe browsing service, upgrade detector, translate, UMA
    '--disable-background-networking',
    // Disable fetching safebrowsing lists, likely redundant due to disable-background-networking
    '--safebrowsing-disable-auto-update',
    // Disable syncing to a Google account
    '--disable-sync',
    // Disable reporting to UMA, but allows for collection
    '--metrics-recording-only',
    // Disable installation of default apps on first run
    '--disable-default-apps',
    // Mute any audio
    '--mute-audio',
    // Skip first run wizards
    '--no-first-run',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-xss-auditor',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-accelerated-2d-canvas',
    '--disk-cache-size=536870912',
    // Ignore cert errors (allow our proxy)
    '--ignore-certificate-errors',
];


let config;

function parseConfig() {
    let args = parser.parseConfig();

    config = {
        flags: DEFAULT_FLAGS,
        dynamic: args,
        maxUrls: maxUrls,
        url_count: url_count,
        csvDelimiter: csvDelimiter,
        depth: depth,
        sameSite: sameSite,
        url_retries: url_retries,
        crawl_retries: crawl_retries,
        collectUrlsWhileCrawling: collectUrlsWhileCrawling,
        shardPath: shardPath,
        clearProfileOnShutdown: clearProfileOnShutdown,
        waitUntil: waitUntil,
        db: {
            user: db_user,
            pass: db_pass,
            host: db_host,
            port: db_port,
            name: db_name,
            engine: db_engine,
        },
        timings: {
            load: load_timeout,
            exec: execution_time_after_load,
            module: module_timeout
        },
        static_modules: modules
    };
}


function getConfig() {
    return config
}

module.exports = {
    parseConfig,
    getConfig
};

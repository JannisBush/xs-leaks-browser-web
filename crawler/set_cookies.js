// hardlinked to node_crawler/modules/set_cookies.js
// from .../node-crawler run
// ln ../main/crawler/set_cookies.js modules/set_cookies.js
const backend = require('../backend');
const browser = require('../crawler');
const util = require('../util');
const args = require('../config').getConfig();
const psl = require('psl');
const db = require('../db');
const redis = require("redis");
const r = redis.createClient();
r.get = require("util").promisify(r.get);

r.on("error", function(error) {
    err("Redis error: " + error);
});

module.exports = {
    Module
};

function Module() {
    // functions have their own this, which means that we cannot get a reference to the object
    // that will now always reference the Module object at any point in the Module functionality
    let that = this;

    this.name = 'example';

    this.setup = async function () {
        // create table which store your information
        let client = await db.getClient();
        //await client.query('CREATE TABLE sometable (id SERIAL PRIMARY KEY, name VARCHAR)');
    };

    this.clean = async function () {
        // get rid of tables which are created in the setup function
    };

    /**
     * This function will be called before the page is visited, prepare event listeners/evaluateOnNewDocuments
     */
    this.before = async function (save) {

        that.chrome = await browser.getChrome(); // dont worry about it
        that.page = await browser.getPage(); // puppeteer page (https://github.com/GoogleChrome/puppeteer/blob/master/docs/api.md#class-page)
        that.client = await db.getClient(); // db client

        // This code is execute before the page code runs
        // It is useful for e.g. hooking dom functionality
        
        // Set cookies here
        let job = await browser.getJob();
        that.cookies = "";
        if (job.cookies) {
            that.cookies = await r.get(job.site);
            that.cookies = JSON.parse(that.cookies);
            log("length of cookies: " + that.cookies.length);
            await that.page.setCookie(...that.cookies);
            that.cookies = await that.page._client.send("Network.getAllCookies"); // Cookies from puppeteer have some additional settings
        } 
        else {
            log("no cookies");
        }

    };
    /**
     * Sample creation of function which should be executed in the context of the page
     */
    this.pageFunc = '(' + function () {
        console.log(document.domain)
    } + ')()';

    this.execute = async function (save) {
        /*
            super fancy javascript that is executed after the page has loaded and the time specified in the config has passed
         */
        // Check if cookies changed, logout etc., is not important for us, as we set the cookies for every request
        let new_cookies = await that.page._client.send("Network.getAllCookies");
        if (JSON.stringify(new_cookies["cookies"]) !== JSON.stringify(that.cookies["cookies"])){
            log("cookies changed! new length:" + new_cookies["cookies"].length);
	        // log(new_cookies);
        }

    };
}

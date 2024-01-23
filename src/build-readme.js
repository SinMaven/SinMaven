const RssParser = require('rss-parser')

const vfile = require('to-vfile')

const remark = require('remark')

const { promisify } = require('util')

const { writeFile } = require('fs')

const { join } = require('path')


const rssParser = new RssParser()

const readmePath = join(__dirname, '..', 'README.md')


;(async () => {

  const feed = await rssParser.parseURL(

    'https://0xrinx.is-cool.dev/rss.xml'

  )

  const file = await remark()

    .use(replaceBlogposts(feed.items))

    .process(vfile.readSync(readmePath))

  await promisify(writeFile)(readmePath, String(file))

})()

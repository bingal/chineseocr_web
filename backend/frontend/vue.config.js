// vue.config.js
module.exports = {
    publicPath: "./",
    chainWebpack: config => {
        config
            .plugin('html')
            .tap(args => {
                args[0].title = 'chineseocr_web-文字涂抹'
                return args
            })
    }
}
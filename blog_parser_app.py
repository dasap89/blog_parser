"""Application for parsing blog articles https://realpython.com/blog/"""

from flask import Flask, render_template,\
    request, flash, url_for, redirect, abort
from flask_mongoengine import MongoEngine
import lxml.html
import requests
from bson.objectid import ObjectId
from config import config

# init flask app
app = Flask(__name__)
app.config.from_object(config['default'])

# init mongodb
db = MongoEngine()
db.init_app(app)

main_url = "https://realpython.com"
blog_url = 'https://realpython.com/blog'
path_all_categories = ".//ul[@id='category']//li//a"
path_all_articles =\
    ".//div[@id='blog-archives']//article[@class='page-header']//h1//a"
path_article_text = ".//div[@class='entry-content clearfix']"


class Articles(db.Document):
    """Make mongodb model for articles"""
    category = db.StringField()
    title = db.StringField()
    text = db.StringField()
    url_article = db.URLField()


class Categories(db.Document):
    """Make mongodb model for categories"""
    title = db.StringField()
    url_category = db.URLField()


def get_content(url):
    """
    getting html content from current url
    :param url:
    :return: page content in string format
    """
    try:
        res = requests.get(url)
    except ConnectionError:
        abort(500)
    if res.status_code < 400:
        return res.content


def parse(html, path):
    """
    parsing html content
    :param html - string with html content:
    :param path - strind with xpath query:
    :return: parsered lxml objects
    """
    try:
        html_tree = lxml.html.fromstring(html)
        result = html_tree.xpath(path)
    except Exception:
        abort(500)
    return result


def parse_categories_list(url):
    """
    Add to mongo db categories if it doesnt exist
    :param url - url current category:
    :return list categories with urls:
    """
    content = get_content(url)
    result = parse(content, path_all_categories)
    categories = []
    if result:
        try:
            for item in result:
                if not Categories.objects(title=item.text_content()):
                    # add category to db
                    Categories(title=item.text_content(),
                               url_category='{0}{1}'.format(
                                   main_url, item.get('href'))).save()
                category = dict()
                category['category'] = item.text_content()
                category['url'] = '{0}{1}'.format(main_url,
                                                  item.get('href'))
                categories.append(category)
        except Exception:
            abort(500)
    return categories


def parse_articles_list(cat_list):
    """
    Add to mongo db articles if it doesnt exist
    :param cat_list - list categories with urls:
    :return:
    """
    if cat_list:
        try:
            for category in cat_list:
                content = get_content(category['url'])
                result = parse(content, path_all_articles)
                for item in result:
                    if not Articles.objects(title=item.text_content()):
                        url_article = '{0}{1}'.format(main_url,
                                                      item.get('href'))
                        # add article to db
                        Articles(
                            category=category['category'],
                            title=item.text_content(),
                            url_article=url_article,
                            text=parse_article_text(url_article)
                        ).save()

        except Exception:
            abort(500)


def parse_article_text(url):
    """
    returning article text
    :param url - article url:
    :return string with article text:
    """
    if url:
        try:
            content = get_content(url)
            result = parse(content, path_article_text)
            content = ''
            for item in result:
                content += item.text_content()
        except Exception:
            abort(500)
    return content


def parse_all(url):
    """
    full cycle parsing(categories adn articles)
    :param url:
    :return:
    """
    categories_list = parse_categories_list(url)
    parse_articles_list(categories_list)


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    start page
    :return: page with total count articles and categoriesin db
    """
    try:
        total_categories = Categories.objects.count()
        total_articles = Articles.objects.count()
        if request.method == 'POST':
            # add task to celery
            flash('All data you will see after few minutes, refresh page.')
            parse_all(blog_url)
            
            return redirect(url_for(
                'index',
                categories=total_categories,
                articles=total_articles
            ))

    except Exception:
        abort(404)

    return render_template(
        'index.html',
        categories=total_categories,
        articles=total_articles
    )


@app.route('/categories/', methods=['GET'])
def categories():
    """
    categories page
    :return: list all categories from db
    """
    try:
        categories = Categories.objects()
    except Exception:
        abort(404)
    return render_template(
        'categories.html',
        categories=categories
    )


@app.route('/articles/', methods=['GET'])
def articles():
    """
    articles page
    :return all articles from db, or current articles with current category,
    or current article(dependency from request params)
    """
    category = request.args.get("category", None)
    article_id = request.args.get("article", None)
    try:
        if category:
            articles = Articles.objects(category=category)
        elif article_id and ObjectId.is_valid(article_id):
            article = Articles.objects.get(id=ObjectId(article_id))
            return render_template('article.html', article=article)
        else:
            articles = Articles.objects()
    except Exception:
        abort(404)
    return render_template(
        'articles.html',
        articles=articles,
        category=category
    )


@app.errorhandler(404)
def not_found(error):
    return render_template('error_404.html'), 404


@app.errorhandler(500)
def server_err(error):
    return render_template('error_500.html'), 500


if __name__ == '__main__':
    app.run()

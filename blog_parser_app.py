"""Application for parsing blog articles https://realpython.com/blog/"""

from flask import Flask, render_template,\
    request, flash, url_for, redirect, abort, jsonify
from flask_mongoengine import MongoEngine
import lxml.html
import requests
from bson.objectid import ObjectId
from config import config
from bson import ObjectId

# init flask app
app = Flask(__name__)
app.config.from_object(config['default'])

# init mongodb
db = MongoEngine()
db.init_app(app)

main_url = "https://realpython.com"
blog_url = 'https://realpython.com/blog'
path_to_all_articles = '//article[@class="page-header"]'
path_to_categories_for_article = './/span[@class="categories"]//a'


class Categories(db.Document):
    """Make mongodb model for categories"""
    title = db.StringField()
    url_category = db.URLField()


class Articles(db.Document):
    """Make mongodb model for articles"""
    category = db.StringField()
    title = db.StringField()
    text = db.StringField()
    categories =  db.ListField(db.ReferenceField(Categories))
    url_article = db.URLField()


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


def parse_all_articles(url):
    """
    Add to mongo db articles and categories per article if it doesnt exist
    :param url - url current category:
    :return list categories with urls:
    """
    content = get_content(url)
    result = parse(content, path_to_all_articles)
    if result:
        try:     
            for item in result:

                item = item.getchildren()
                article, categories = item
                categories = categories.xpath(path_to_categories_for_article)

                article_title = article.text_content()


                if not Articles.objects(title=article_title):

                    Articles(
                        title=article_title,
                        url_article='{0}{1}'.format(main_url, article.getchildren()[0].get('href')),
                    ).save()
                
                article_obj = Articles.objects(title=article_title)

                
                for category in categories:
                    category_title = category.text_content()                

                    if not Categories.objects(title=category_title):
                        # add category to db
                        Categories(title=category_title, url_category='{0}{1}'.format(main_url, category.get('href'))).save()
  
                    category_obj = Categories.objects.get(title=category_title)

                    if category_obj not in Articles.objects.get(title=article_title).categories:
                        article_obj.update_one(push__categories=[category_obj])
            
        except Exception:
            abort(500)
    else:
        return abort(500)    


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

            # parse_all(blog_url)
            parse_all_articles(blog_url)

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
    # category = request.args.get("category", None)
    # print category
    # if category:
    #     try:
    #         category = Categories.objects.get(title=category)
    #         print category
    #         articles = Articles.objects.filter(categories__in=[category])
    #     except Exception:
    #         abort(404)
    #     return render_template('categories.html', categories=category, articles=articles)
    # else:
    categories = Categories.objects()
    return render_template('categories.html', categories=categories)


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
            category = Categories.objects.get(title=category)
            articles = Articles.objects.filter(categories__in=[category])
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


# APIs

@app.route('/api/categories/', methods=['GET'])
def api_get_categories():
    """
    articles page
    :return all articles from db, or current articles with current category,
    or current article(dependency from request params)
    """
    categories = Categories.objects()
    return jsonify({'categories': categories})


@app.route('/api/categories/<string:category_name>', methods=['GET'])
def api_get_articles_by_category(category_name):
    """
    articles page
    :return all articles from db, or current articles with current category,
    or current article(dependency from request params)
    """
    category = Categories.objects.get(title=category_name)
    articles = Articles.objects.filter(categories__in=[category])
    return jsonify({'category': category, 'articles': articles})


@app.route('/api/articles/', methods=['GET'])
def api_get_articles():
    """
    articles page
    :return all articles from db, or current articles with current category,
    or current article(dependency from request params)
    """
    articles = Articles.objects()
    return jsonify({'articles': articles})

@app.route('/api/articles/<string:article_id>', methods=['GET'])
def api_get_one_article(article_id):
    try:
        article_id = ObjectId(article_id)
        article = Articles.objects.get(id=article_id)
        return jsonify({'article': article})
    except:
        return jsonify({'article': "Not found article with id {}".format(article_id)})


# Error handlers

@app.errorhandler(404)
def not_found(error):
    return render_template('error_404.html'), 404


@app.errorhandler(500)
def server_err(error):
    return render_template('error_500.html'), 500


if __name__ == '__main__':
    app.run(threaded=True)

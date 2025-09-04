import 'package:flutter/material.dart';
import '../models/news.dart';
import '../services/news_service.dart';
import 'news_detail_page.dart';

class NewsPage extends StatefulWidget {
  const NewsPage({super.key});

  @override
  State<NewsPage> createState() => _NewsPageState();
}

class _NewsPageState extends State<NewsPage> {
  int _currentPage = 1;
  int _lastPage = 1;
  bool _isLoading = true;
  bool _isSearching = false;
  String _searchQuery = "";

  List<News> _articles = [];
  List<News> _filteredArticles = [];

  @override
  void initState() {
    super.initState();
    _fetchArticles();
  }

  Future<void> _fetchArticles({int page = 1}) async {
    setState(() => _isLoading = true);

    try {
      final result = await NewsService.fetchNews(page: page);
      setState(() {
        _articles = result['articles'];
        _filteredArticles = _articles;
        _currentPage = result['currentPage'];
        _lastPage = result['lastPage'];
      });
    } catch (e) {
      debugPrint("❌ Error fetching articles: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _startSearch() {
    setState(() {
      _isSearching = true;
    });
  }

  void _stopSearch() {
    setState(() {
      _isSearching = false;
      _searchQuery = "";
      _filteredArticles = _articles;
    });
  }

  void _filterArticles(String query) {
    setState(() {
      _searchQuery = query;
      _filteredArticles = _articles
          .where(
            (a) =>
                a.title.toLowerCase().contains(query.toLowerCase()) ||
                (a.content ?? "").toLowerCase().contains(query.toLowerCase()),
          )
          .toList();
    });
  }

  PreferredSizeWidget _buildAppBar() {
    if (_isSearching) {
      return AppBar(
        backgroundColor: Colors.green[700],
        title: TextField(
          autofocus: true,
          decoration: const InputDecoration(
            hintText: "Search news...",
            border: InputBorder.none,
            hintStyle: TextStyle(color: Colors.white70),
          ),
          style: const TextStyle(color: Colors.white),
          onChanged: _filterArticles,
        ),
        actions: [
          IconButton(icon: const Icon(Icons.close), onPressed: _stopSearch),
        ],
      );
    }

    return AppBar(
      title: const Text(
        "Saudi Football News",
        style: TextStyle(fontWeight: FontWeight.bold),
      ),
      centerTitle: true,
      backgroundColor: Colors.green[700],
      elevation: 0,
      actions: [
        IconButton(icon: const Icon(Icons.search), onPressed: _startSearch),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: _buildAppBar(),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Expanded(
                  child: _filteredArticles.isEmpty
                      ? const Center(
                          child: Text(
                            "No articles found",
                            style: TextStyle(fontSize: 16),
                          ),
                        )
                      : ListView.builder(
                          itemCount: _filteredArticles.length,
                          itemBuilder: (context, index) {
                            final article = _filteredArticles[index];
                            return Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 6,
                              ),
                              child: Card(
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                elevation: 3,
                                clipBehavior: Clip.antiAlias,
                                child: InkWell(
                                  onTap: () {
                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) =>
                                            NewsDetailPage(article: article),
                                      ),
                                    );
                                  },
                                  child: Row(
                                    children: [
                                      if (article.image != null)
                                        Image.network(
                                          article.image!,
                                          width: 120,
                                          height: 90,
                                          fit: BoxFit.cover,
                                        ),
                                      Expanded(
                                        child: Padding(
                                          padding: const EdgeInsets.all(12.0),
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                article.title,
                                                style: const TextStyle(
                                                  fontSize: 16,
                                                  fontWeight: FontWeight.w600,
                                                ),
                                                maxLines: 2,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                              const SizedBox(height: 6),
                                              Text(
                                                "${article.publishedAt!.toLocal()}"
                                                    .split(" ")[0],
                                                style: TextStyle(
                                                  fontSize: 12,
                                                  color: Colors.grey[600],
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                ),
                // Only show pagination if not searching
                if (!_isSearching)
                  Container(
                    padding: const EdgeInsets.all(12),
                    color: Colors.white,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.chevron_left),
                          onPressed: _currentPage > 1
                              ? () => _fetchArticles(page: _currentPage - 1)
                              : null,
                        ),
                        Text(
                          "$_currentPage / $_lastPage",
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        IconButton(
                          icon: const Icon(Icons.chevron_right),
                          onPressed: _currentPage < _lastPage
                              ? () => _fetchArticles(page: _currentPage + 1)
                              : null,
                        ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }
}

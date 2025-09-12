import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import '../models/news.dart';
import '../services/news_service.dart';
import 'news_detail_page.dart';
import '../utils/custom_cache_manager.dart';

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
    _fetchArticles(page: 1);
  }

  Future<void> _fetchArticles({int page = 1}) async {
    if (page == 1) setState(() => _isLoading = true);

    try {
      final result = await NewsService.fetchNews(page: page);
      final fetched = List<News>.from(result['articles'] as List<News>);

      setState(() {
        _articles = fetched;
        _filteredArticles = _searchQuery.isEmpty
            ? List<News>.from(_articles)
            : _articles
                  .where(
                    (a) =>
                        a.title.toLowerCase().contains(
                          _searchQuery.toLowerCase(),
                        ) ||
                        (a.content ?? "").toLowerCase().contains(
                          _searchQuery.toLowerCase(),
                        ),
                  )
                  .toList();

        _currentPage = result['currentPage'] as int;
        _lastPage = result['lastPage'] as int;
      });
    } catch (e) {
      debugPrint('Error fetching articles: $e');
    } finally {
      if (page == 1) setState(() => _isLoading = false);
    }
  }

  void _startSearch() => setState(() => _isSearching = true);

  void _stopSearch() {
    setState(() {
      _isSearching = false;
      _searchQuery = "";
      _filteredArticles = List<News>.from(_articles);
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
    return AppBar(
      flexibleSpace: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF1B5E20), Color(0xFF2E7D32)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
      ),
      title: const Text('Saudi Football News'),
      actions: [
        IconButton(icon: const Icon(Icons.search), onPressed: _startSearch),
      ],
    );
  }

  Widget _buildSearchBar() {
    if (!_isSearching) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: TextField(
        autofocus: true,
        decoration: InputDecoration(
          hintText: 'Search articles...',
          filled: true,
          fillColor: Colors.white,
          prefixIcon: const Icon(Icons.search),
          suffixIcon: IconButton(
            icon: const Icon(Icons.close),
            onPressed: _stopSearch,
          ),
          contentPadding: const EdgeInsets.symmetric(vertical: 12),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide.none,
          ),
        ),
        onChanged: _filterArticles,
      ),
    );
  }

  String _sourceFromLink(String? link) {
    if (link == null || link.isEmpty) return 'Source';
    try {
      final host = Uri.parse(link).host;
      return host.isNotEmpty ? host.replaceFirst('www.', '') : 'Source';
    } catch (_) {
      return 'Source';
    }
  }

  Widget _articleCard(BuildContext context, News article) {
    final heroTag = article.link.isNotEmpty ? article.link : article.title;
    final hasImage = article.image != null && article.image!.trim().isNotEmpty;
    final sourceText = _sourceFromLink(article.link);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: GestureDetector(
        onTap: () async {
          if (hasImage) {
            try {
              final provider = CachedNetworkImageProvider(
                article.image!,
                cacheManager: CustomCacheManager.instance,
              );
              await precacheImage(provider, context);
            } catch (_) {}
          }

          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => NewsDetailPage(article: article)),
          );
        },
        child: Card(
          clipBehavior: Clip.antiAlias,
          child: SizedBox(
            height: 140,
            child: Row(
              children: [
                Expanded(
                  flex: 4,
                  child: Stack(
                    children: [
                      Positioned.fill(
                        child: Hero(
                          tag: heroTag,
                          child: hasImage
                              ? CachedNetworkImage(
                                  imageUrl: article.image!,
                                  cacheManager: CustomCacheManager.instance,
                                  fit: BoxFit.cover,
                                  placeholder: (c, u) =>
                                      Container(color: Colors.grey[300]),
                                  errorWidget: (c, u, e) => Container(
                                    color: Colors.grey[300],
                                    child: const Icon(Icons.broken_image),
                                  ),
                                )
                              : Container(
                                  color: Colors.grey[300],
                                  child: const Icon(Icons.image_not_supported),
                                ),
                        ),
                      ),
                      Positioned.fill(
                        child: Container(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [
                                Colors.transparent,
                                Colors.black.withOpacity(0.35),
                              ],
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  flex: 6,
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (article.category != null &&
                            article.category!.isNotEmpty)
                          Container(
                            margin: const EdgeInsets.only(bottom: 4),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.blue.shade50,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              article.category!,
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.blue.shade800,
                                fontWeight: FontWeight.w600,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        Expanded(
                          child: Text(
                            article.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                        ),
                        Row(
                          children: [
                            Flexible(
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.green.shade50,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  sourceText,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: Colors.green.shade800,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              "${article.publishedAt.toLocal()}".split(' ')[0],
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.grey[600],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _onRefresh() async => _fetchArticles(page: 1);

  Widget _buildPagination() {
    const visibleCount = 5;
    int startPage = (_currentPage - (visibleCount ~/ 2)).clamp(1, _lastPage);
    int endPage = (startPage + visibleCount - 1).clamp(1, _lastPage);

    if (endPage - startPage + 1 < visibleCount) {
      startPage = (endPage - visibleCount + 1).clamp(1, _lastPage);
    }

    List<Widget> pages = [];

    pages.add(
      IconButton(
        icon: const Icon(Icons.chevron_left),
        onPressed: _currentPage > 1
            ? () => _fetchArticles(page: _currentPage - 1)
            : null,
      ),
    );

    for (int i = startPage; i <= endPage; i++) {
      pages.add(
        TextButton(
          onPressed: () => _fetchArticles(page: i),
          child: Text(
            "$i",
            style: TextStyle(
              fontWeight: i == _currentPage
                  ? FontWeight.bold
                  : FontWeight.normal,
              color: i == _currentPage ? Colors.blue : Colors.black,
            ),
          ),
        ),
      );
    }

    pages.add(
      IconButton(
        icon: const Icon(Icons.chevron_right),
        onPressed: _currentPage < _lastPage
            ? () => _fetchArticles(page: _currentPage + 1)
            : null,
      ),
    );

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: pages),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: _buildAppBar(),
      body: Column(
        children: [
          _buildSearchBar(),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _filteredArticles.isEmpty
                ? const Center(child: Text('No articles found'))
                : RefreshIndicator(
                    onRefresh: _onRefresh,
                    child: ListView.builder(
                      key: const PageStorageKey('news_list'),
                      cacheExtent: 1200,
                      itemCount: _filteredArticles.length,
                      itemBuilder: (context, index) =>
                          _articleCard(context, _filteredArticles[index]),
                    ),
                  ),
          ),
          if (!_isSearching)
            Container(
              padding: const EdgeInsets.all(12),
              color: Colors.white,
              child: _buildPagination(),
            ),
        ],
      ),
    );
  }
}

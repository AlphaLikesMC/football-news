import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/news.dart';

class NewsService {
  // Keep this set to the API you verified. Change here if you need to point to another host/tunnel.
  static const String baseUrl =
      "https://football-news-production.up.railway.app/api/news";

  /// Fetch paginated news (defensive parsing + logging)
  static Future<Map<String, dynamic>> fetchNews({
    int page = 1,
    int perPage = 10,
  }) async {
    final url = Uri.parse("$baseUrl?page=$page&per_page=$perPage");
    try {
      final response = await http.get(url).timeout(const Duration(seconds: 10));
      debugPrint("NewsService: GET $url -> ${response.statusCode}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        final rawList = data['data'] as List<dynamic>? ?? [];
        final List<News> articles = [];

        for (final raw in rawList) {
          try {
            final Map<String, dynamic> map = raw is Map<String, dynamic>
                ? raw
                : Map<String, dynamic>.from(raw);
            articles.add(News.fromJson(map));
          } catch (e, st) {
            debugPrint("NewsService: skip item - parse error: $e\n$st");
            continue;
          }
        }

        debugPrint(
          "NewsService: parsed ${articles.length} articles (raw ${rawList.length})",
        );

        return {
          'articles': articles,
          'currentPage': data['current_page'] ?? data['currentPage'] ?? 1,
          'lastPage': data['last_page'] ?? data['lastPage'] ?? 1,
          'total': data['total'] ?? 0,
        };
      } else {
        debugPrint("NewsService: non-200 body: ${response.body}");
        throw Exception("Failed to load news (status ${response.statusCode})");
      }
    } catch (e) {
      debugPrint("NewsService: fetch error: $e");
      rethrow;
    }
  }

  /// Fetch single news item
  static Future<News> fetchNewsDetail(int id) async {
    final url = Uri.parse("$baseUrl/$id");
    final response = await http.get(url).timeout(const Duration(seconds: 10));
    if (response.statusCode == 200) {
      return News.fromJson(jsonDecode(response.body));
    } else {
      throw Exception(
        "Failed to load news detail (status ${response.statusCode})",
      );
    }
  }
}

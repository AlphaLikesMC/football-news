import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/news.dart';

class NewsService {
  static const String baseUrl = "https://045b7fc1ed83.ngrok-free.app/api/news";

  /// Fetch paginated news
  static Future<Map<String, dynamic>> fetchNews({
    int page = 1,
    int perPage = 10,
  }) async {
    final url = Uri.parse("$baseUrl?page=$page&per_page=$perPage");
    final response = await http.get(url);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);

      // Laravel paginate response has "data" for items
      List<News> articles = (data['data'] as List)
          .map((json) => News.fromJson(json))
          .toList();

      return {
        'articles': articles,
        'currentPage': data['current_page'],
        'lastPage': data['last_page'],
        'total': data['total'],
      };
    } else {
      throw Exception("Failed to load news (status ${response.statusCode})");
    }
  }

  /// Fetch single news item
  static Future<News> fetchNewsDetail(int id) async {
    final url = Uri.parse("$baseUrl/$id");
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return News.fromJson(jsonDecode(response.body));
    } else {
      throw Exception(
        "Failed to load news detail (status ${response.statusCode})",
      );
    }
  }
}

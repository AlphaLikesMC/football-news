class News {
  final String title;
  final String link;
  final String? description;
  final String? content;
  final String? image;
  final DateTime publishedAt;

  News({
    required this.title,
    required this.link,
    this.description,
    this.content,
    this.image,
    required this.publishedAt,
  });

  factory News.fromJson(Map<String, dynamic> json) {
    return News(
      title: json['title'] ?? '',
      link: json['link'] ?? '',
      description: json['description'],
      content: json['content'],
      image: json['image'],
      publishedAt: DateTime.parse(json['published_at']),
    );
  }
}

class News {
  final String title;
  final String link;
  final String? description;
  final String? content;
  final String? image;
  final DateTime publishedAt;
  final String? category; // ✅ NEW FIELD

  News({
    required this.title,
    required this.link,
    this.description,
    this.content,
    this.image,
    required this.publishedAt,
    this.category, // ✅ include in constructor
  });

  factory News.fromJson(Map<String, dynamic> json) {
    final rawPublished =
        json['published_at'] ?? json['publishedAt'] ?? json['published_at_raw'];

    DateTime published;
    try {
      if (rawPublished == null) {
        published = DateTime.now();
      } else if (rawPublished is String) {
        published = DateTime.tryParse(rawPublished) ?? DateTime.now();
      } else if (rawPublished is int) {
        published = DateTime.fromMillisecondsSinceEpoch(rawPublished * 1000);
      } else if (rawPublished is double) {
        published = DateTime.fromMillisecondsSinceEpoch(
          (rawPublished * 1000).toInt(),
        );
      } else {
        published = DateTime.now();
      }
    } catch (_) {
      published = DateTime.now();
    }

    return News(
      title: json['title'] ?? '',
      link: json['link'] ?? '',
      description: json['description'],
      content: json['content'],
      image: json['image'],
      publishedAt: published,
      category: json['category'], // ✅ parse category
    );
  }
}

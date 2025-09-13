import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_widget_from_html/flutter_widget_from_html.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/news.dart';
import '../utils/custom_cache_manager.dart';

class NewsDetailPage extends StatelessWidget {
  final News article;

  const NewsDetailPage({super.key, required this.article});

  Widget _buildContent(BuildContext context) {
    final content =
        article.content ?? article.description ?? "No content available";

    // Clean up the content by removing escape sequences and fixing HTML
    String cleanContent = content
        .replaceAll(r'\u003C', '<')
        .replaceAll(r'\u003E', '>')
        .replaceAll(r'\"', '"')
        .replaceAll(r'\n', '\n');

    return HtmlWidget(
      cleanContent,
      textStyle: Theme.of(context).textTheme.bodyMedium,
      onTapUrl: (url) async {
        final uri = Uri.tryParse(url);
        if (uri != null && await canLaunchUrl(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
          return true;
        }
        return false;
      },
      customStylesBuilder: (element) {
        if (element.localName == 'p') {
          return {'margin': '0 0 12px 0'};
        }
        if (element.localName == 'strong') {
          return {'font-weight': 'bold'};
        }
        return null;
      },
      customWidgetBuilder: (element) {
        // Handle images in HTML content
        if (element.localName == 'img') {
          final src = element.attributes['src'];
          if (src != null) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: CachedNetworkImage(
                imageUrl: src,
                cacheManager: CustomCacheManager.instance,
                width: double.infinity,
                fit: BoxFit.contain,
                placeholder: (context, url) =>
                    Container(height: 220, color: Colors.grey[300]),
                errorWidget: (context, url, error) => Container(
                  height: 220,
                  color: Colors.grey[300],
                  child: const Icon(Icons.broken_image),
                ),
              ),
            );
          }
        }
        return null;
      },
    );
  }

  String _sourceFromLink(String? link) {
    if (link == null || link.isEmpty) return 'Source';
    try {
      final host = Uri.parse(link).host;
      if (host.isEmpty) return 'Source';
      return host.replaceFirst('www.', '');
    } catch (e) {
      return 'Source';
    }
  }

  @override
  Widget build(BuildContext context) {
    final heroTag = article.image ?? article.title;
    final hasImage = article.image != null && article.image!.trim().isNotEmpty;
    final sourceText = _sourceFromLink(article.link);

    return Scaffold(
      backgroundColor: Colors.grey[100],
      body: SafeArea(
        child: Column(
          children: [
            // top visual with back/share
            SizedBox(
              height: 280,
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
                            Colors.black.withOpacity(0.45),
                          ],
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    left: 12,
                    top: 12,
                    child: CircleAvatar(
                      backgroundColor: Colors.black.withOpacity(0.4),
                      child: IconButton(
                        icon: const Icon(Icons.arrow_back, color: Colors.white),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      article.title,
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.green.shade50,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            sourceText,
                            style: TextStyle(color: Colors.green.shade800),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          "${article.publishedAt.toLocal()}".split(" ")[0],
                          style: TextStyle(color: Colors.grey[600]),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    _buildContent(context),
                    const SizedBox(height: 20),
                    Center(
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.open_in_new),
                        label: const Text("Read Original"),
                        onPressed: () async {
                          final uri = Uri.tryParse(article.link);
                          if (uri != null && await canLaunchUrl(uri)) {
                            await launchUrl(
                              uri,
                              mode: LaunchMode.externalApplication,
                            );
                          } else {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text("Unable to open link"),
                              ),
                            );
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

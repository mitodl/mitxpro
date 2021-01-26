"""CMS templatetags"""

from re import findall
from urllib.parse import quote_plus

from django import template

from wagtail.images.templatetags.wagtailimages_tags import image
from wagtail_lazyimages.templatetags.lazyimages_tags import LazyImageNode

register = template.Library()


class CustomLazyImageNode(LazyImageNode):
    """
    An extention to Wagtail-lazyimages library's wagtail_lazyimages.templatetags.lazyimages_tags.LazyImageNode
    class for customizations
    """

    def render(self, context):
        """
        This method overrides LazyImageNode's render method to add file-hashes to image urls for better caching

        Returns:
            str or None: An image tag with required src (having tiny blurry placeholder image) and
                data-src (having full-scale image) attribute values
        """
        img = self.image_expr.resolve(context)
        if not img:
            return ""

        file_hash = quote_plus(img.file_hash)
        raw_img_tag = super().render(context)

        for link in findall(r"src=(.+?)\s", raw_img_tag):
            raw_img_tag = raw_img_tag.replace(
                link, f"{link[:-1]}?v={file_hash}{link[-1]}"
            )

        return raw_img_tag


@register.tag(name="wagtail_lazy_image")
def wagtail_lazy_image(img, filter_spec):
    """
    Generates an image tag using Wagtail-lazyimages library and appends a version to the path to enable effective caching

    This method is inspired by wagtail_lazyimages.templatetags.lazyimages_tags.lazy_image of Wagtail-lazyimages library

    Args:
        img (wagtail.images.models.Image): The image for which an image template tag will be generated
        filter_spec (str): A filter specification for the image (see Wagtail docs)

    Returns:
        CustomLazyImageNode object or None/empty str: A complete lazy loading image tag
    """

    if not img:
        return ""

    node = image(img, filter_spec)
    return CustomLazyImageNode(
        node.image_expr,
        node.filter_spec,
        attrs=node.attrs,
        output_var_name=node.output_var_name,
    )

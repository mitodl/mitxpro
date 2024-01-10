# Generated by Django 3.2.23 on 2024-01-09 21:50

import cms.models
from django.db import migrations, models
import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
import wagtail.images.blocks


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0089_log_entry_data_json_null_to_object'),
        ('wagtailimages', '0025_alter_image_file_alter_rendition_file'),
        ('wagtaildocs', '0012_uploadeddocument'),
        ('cms', '0067_wagtail_5_upgrade'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompaniesLogoCarouselSection',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('images', wagtail.fields.StreamField([('image', wagtail.images.blocks.ImageChooserBlock(help_text='Choose an image to upload.'))], help_text='Add images for this section.', use_json_field=True)),
                ('heading', wagtail.fields.RichTextField(help_text='The main heading of the Companies Logo Carousel section.')),
            ],
            options={
                'verbose_name': 'Companies Logo Carousel',
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='LearningStrategyFormSection',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('heading', wagtail.fields.RichTextField(help_text='Enter the main heading for the learning strategy form section.')),
                ('subhead', wagtail.fields.RichTextField(help_text='A subheading to provide additional context or information.')),
            ],
            options={
                'verbose_name': 'Learning Strategy Form',
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='SuccessStoriesSection',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('heading', wagtail.fields.RichTextField(help_text='The main heading for the success stories section.')),
                ('subhead', wagtail.fields.RichTextField(help_text='A subheading to provide additional context or information.')),
                ('success_stories', wagtail.fields.StreamField([('success_story', wagtail.blocks.StructBlock([('title', wagtail.blocks.CharBlock(help_text='Enter the title of the success story.', max_length=255)), ('image', wagtail.images.blocks.ImageChooserBlock(help_text='Select an image to accompany the success story.')), ('content', wagtail.blocks.TextBlock(help_text='Provide the detailed content or description of the success story.')), ('call_to_action', wagtail.blocks.CharBlock(default='Read More', help_text="Enter the text for the call-to-action button (e.g., 'Read More').", max_length=100)), ('action_url', wagtail.blocks.URLBlock(help_text='Provide the URL that the call-to-action button should link to.'))]))], help_text='Manage the individual success stories. Each story is a separate block.', use_json_field=True)),
            ],
            options={
                'verbose_name': 'Success Stories',
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='LearningJourneySection',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('heading', wagtail.fields.RichTextField(help_text='The main heading of the learning journey section.')),
                ('description', wagtail.fields.RichTextField(help_text='A detailed description of the learning journey section.')),
                ('journey_items', wagtail.fields.StreamField([('journey', wagtail.blocks.TextBlock(icon='plus'))], help_text='Enter the text for this learning journey item.', use_json_field=True)),
                ('call_to_action', models.CharField(default='View Full Diagram', help_text='Text for the call-to-action button.', max_length=30)),
                ('action_url', models.URLField(blank=True, help_text='URL for the call-to-action button, used if no PDF is linked.', null=True)),
                ('journey_image', models.ForeignKey(blank=True, help_text='Optional image to visually represent the learning journey at least 560x618 pixels.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image')),
                ('pdf_file', models.ForeignKey(blank=True, help_text='PDF document linked to the call-to-action button, prioritized over the URL.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtaildocs.document')),
            ],
            options={
                'verbose_name': 'Learning Journey',
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='EnterprisePage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('headings', wagtail.fields.StreamField([('heading', wagtail.blocks.StructBlock([('upper_head', wagtail.blocks.CharBlock(help_text='The main heading.', max_length=25)), ('middle_head', wagtail.blocks.CharBlock(help_text='Secondary heading.', max_length=25)), ('bottom_head', wagtail.blocks.CharBlock(help_text='Lower heading.', max_length=25))]))], help_text='Add banner headings for this page.', use_json_field=True)),
                ('description', wagtail.fields.RichTextField(help_text='Enter a description for the call-to-action section under banner.')),
                ('action_title', models.CharField(help_text='The text to show on the call to action button', max_length=100)),
                ('background_image', models.ForeignKey(blank=True, help_text='Background image size must be at least 1440x613 pixels.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image')),
                ('overlay_image', models.ForeignKey(blank=True, help_text='Select an overlay image for the banner section at leasr 544x444 pixels.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image')),
            ],
            options={
                'verbose_name': 'Enterprise',
            },
            bases=(cms.models.WagtailCachedPageMixin, 'wagtailcore.page'),
        ),
    ]

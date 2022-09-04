from .views import StoryDetailView, StoryLikeView, StoryListView
from django.urls import path

urlpatterns =[
    path('story_like/', StoryLikeView.as_view({'post':'post'}), name="story_like"),
    path('story_detail/', StoryDetailView.as_view(), name='story_detail'),
    path('story_list/', StoryListView.as_view({'get': 'list'}), name='story_list'),
]

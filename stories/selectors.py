from datetime import datetime
from dataclasses import dataclass
from collections import Counter
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Aggregate, Value, CharField, Case, When, Exists, OuterRef, Subquery
from django.db.models.functions import Concat, Substr
from users.models import User
import stories as st
from stories.models import Story, StoryPhoto, StoryComment, StoryMap
from curations.models import Curation, Curation_Story


# for caching
# from core.caches import get_cache


class GroupConcat(Aggregate):
    # Postgres ArrayAgg similar(not exactly equivalent) for sqlite & mysql
    # https://stackoverflow.com/questions/10340684/group-concat-equivalent-in-django
    function = 'GROUP_CONCAT'
    separator = ','

    def __init__(self, expression, distinct=False, ordering=None, **extra):
        super(GroupConcat, self).__init__(expression,
                                          distinct='DISTINCT ' if distinct else '',
                                          ordering=' ORDER BY %s' % ordering if ordering is not None else '',
                                          output_field=CharField(),
                                          **extra)

    def as_mysql(self, compiler, connection, separator=separator):
        return super().as_sql(compiler,
                              connection,
                              template='%(function)s(%(distinct)s%(expressions)s%(ordering)s%(separator)s)',
                              separator=' SEPARATOR \'%s\'' % separator)

    def as_sql(self, compiler, connection, **extra):
        return super().as_sql(compiler,
                              connection,
                              template='%(function)s(%(distinct)s%(expressions)s%(ordering)s)',
                              **extra)


@dataclass
class StoryDto:
    id: int
    title: str
    place_name: str
    story_review: str
    preview: str
    html_content: str
    tag: str
    views: int
    story_like: str
    like_cnt: str
    comment_cnt: str
    category: int
    semi_category: str
    writer: str
    writer_is_verified: bool
    nickname: str
    profile: str
    created: datetime
    map_image: str
    rep_pic: str
    extra_pics: list[str]
    writer_is_followed : bool = None

@dataclass
class SamePlaceStoryDto:
    id: int
    title: str
    place_name:  str
    preview: str
    writer: str
    writer_is_verified: bool
    nickname: str
    created: datetime
    rep_pic: str
    extra_pics: list[str]



def append_media_url(rest):
    return settings.MEDIA_URL + rest


class StoryCoordinatorSelector:
    def __init__(self, user: User):
        self.user = user

    # @get_cache('story:detail:', 'story_id')
    def detail(self, story_id: int):
        story = StorySelector.detail(story_id=story_id)

        story_like = StoryLikeSelector.likes(
            story_id=story.id,
            user=self.user,
        )
        semi_cate = semi_category(story.id)
        writer_is_followed = self.user.follows.filter(pk=story.writer.pk).exists()
        
        dto = StoryDto(
            id=story.id,
            title=story.title,
            place_name=story.place_name,
            story_review=story.story_review,
            preview=story.preview,
            html_content=story.html_content,
            tag=story.tag,
            views=story.views,
            story_like=story_like,
            like_cnt=story.story_like_cnt,
            comment_cnt=len(story.comments.all()),
            category=story.category,
            semi_category=semi_cate,
            writer=story.writer,
            writer_is_verified=story.writer_is_verified,
            nickname=story.nickname,
            profile=story.profile,
            created=story.created,
            map_image=story.map_image,
            rep_pic=story.rep_pic.url,
            extra_pics=[photo.image.url for photo in story.photos.all()[0:2]],
            writer_is_followed=writer_is_followed
        )

        if story.extra_pics is not None:
        
            dto.extra_pics = map(
                append_media_url, story.extra_pics.split(',')[:3])

        return dto


def semi_category(story_id: int):
    '''
        스토리의 세부 category를 알려 주기 위한 함수
    '''
    story = get_object_or_404(Story, id=story_id)
    place = story.place
    result = []
    vegan = place.vegan_category
    if vegan != '':
        result.append(vegan)
    tumblur = place.tumblur_category
    if tumblur == True:
        tumblur = '텀블러 사용 가능'
        result.append(tumblur)
    reusable = place.reusable_con_category
    if reusable == True:
        reusable = '용기내 가능'
        result.append(reusable)
    pet = place.pet_category
    if pet == True:
        pet = '반려동물 출입 가능'
        result.append(pet)
    cnt = len(result)
    ret_result = ""
    for i in range(cnt):
        if i == cnt - 1:
            ret_result = ret_result + result[i]
        else:
            ret_result = ret_result + result[i] + ', '
    return ret_result


class StorySelector:
    def __init__(self):
        pass

    @staticmethod
    def detail(story_id: int, extra_fields: dict = {}):
        stories = Story.objects.all()

        for story in stories:
            if not StoryMap.objects.filter(story=story).exists():
                st.services.StoryMapService.create(story=story)

        return Story.objects.annotate(
            place_name=F('place__place_name'),
            category=F('place__category'),
            writer_is_verified=F('writer__is_verified'),
            nickname=F('writer__nickname'),
            profile=Concat(Value(settings.MEDIA_URL),
                           F('writer__profile_image'),
                           output_field=CharField()),
            map_image=Concat(Value(settings.MEDIA_URL),
                             F('map_photos__map'),
                             output_field=CharField()),
            extra_pics=GroupConcat('photos__image'),
            ** extra_fields
        ).get(id=story_id)

    @staticmethod
    def recommend_list(story_id: int):
        story = Story.objects.get(id=story_id)
        q = Q(place__category=story.place.category)
        recommend_story = Story.objects.filter(q).exclude(id=story_id).annotate(
            writer_is_verified=F('writer__is_verified')
        )

        return recommend_story

    @staticmethod
    def list(search: str = '', order: str = '', filter: list = []):
        q = Q()
        q.add(Q(title__icontains=search) |
              Q(place__place_name__icontains=search) |  # 스토리 제목 또는 내용 검색
              Q(place__category__icontains=search) |
              Q(tag__icontains=search), q.AND)

        if len(filter) > 0:
            query = None
            for element in filter:
                if query is None:
                    query = Q(place__category=element)
                else:
                    query = query | Q(place__category=element)
            q.add(query, q.AND)

        order_by_time = {'latest': '-created', 'oldest': 'created'}
        order_by_likes = {'hot': '-story_like_cnt'}

        if order in order_by_time:
            order = order_by_time[order]
        if order in order_by_likes:
            order = order_by_likes[order]

        stories = Story.objects.filter(q).annotate(
            place_name=F('place__place_name'),
            category=F('place__category'),
            writer_is_verified=F('writer__is_verified'),
            nickname=F('writer__nickname'),
            profile=Concat(Value(settings.MEDIA_URL),
                           F('writer__profile_image'),
                           output_field=CharField()),
            extra_pics=GroupConcat('photos__image'),
        ).order_by(order)

        for story in stories:
            story.rep_pic = story.rep_pic.url
            if story.extra_pics is not None:
                story.extra_pics = map(
                    append_media_url, story.extra_pics.split(',')[:3])

        return stories


class StoryLikeSelector:
    def __init__(self):
        pass

    @staticmethod
    def likes(story_id: int, user: User):
        story = Story.objects.get(id=story_id)
        # 좋아요가 존재하는 지 안하는 지 확인
        if story.story_likeuser_set.filter(pk=user.pk).exists():
            return True
        else:
            return False


class MapMarkerSelector:
    def __init__(self, user: User):
        self.user = user

    @staticmethod
    def map(story_id: int):
        story = Story.objects.get(id=story_id)
        place = story.place

        return place


class StoryCommentSelector:
    def __init__(self):
        pass

    def isWriter(self, story_comment_id: int, user: User):
        return StoryComment.objects.get(id=story_comment_id).writer == user

    def likes(story_comment: StoryComment, user: User):
        return story_comment.likeuser_set.filter(pk=user.pk).exists()

    @staticmethod
    def list(story_id: int, user: User):
        story = Story.objects.get(id=story_id)
        q = Q(story=story)

        story_comments = StoryComment.objects.filter(q).annotate(
            nickname=F('writer__nickname'),
            email=F('writer__email'),
            profile_image=Concat(Value(settings.MEDIA_URL),
                                 F('writer__profile_image'),
                                 output_field=CharField()),
            user_likes=Case(
                When(Exists(StoryComment.likeuser_set.through.objects.filter(
                    storycomment_id=OuterRef('id'),
                    user_id=user.pk
                )),
                    then=Value(1)),
                default=Value(0),
            ),
        ).values(
            'id',
            'story',
            'content',
            'nickname',
            'email',
            'mention',
            'profile_image',
            'user_likes',
            'like_cnt',
            'created_at',
            'updated_at',
        ).order_by('id')

        return story_comments

class StoryIncludedCurationSelector:
    def __init__(self, user:User):
        self.user = user

    def list(self, story_id: int):
        included_curation = Curation.objects.filter(short_curations__story__id=story_id).annotate(
            rep_pic=Case(
                When(
                    photos__image=None,
                    then=None
                ),
                default=Concat(Value(settings.MEDIA_URL),
                               F('photos__image'),
                               output_field=CharField())
            ),
        )

        return included_curation
    
class SamePlaceStorySelector:
    def __init__(self, user:User):
        self.user = user
    
    def list(self, story_id: int):
        story_place_subquery = Story.objects.filter(id=story_id).values('place')

        same_place_stories = Story.objects.filter(place=Subquery(story_place_subquery)).select_related('writer', 'place').prefetch_related('photos').exclude(id=story_id)

        story_dtos = []

        for story in same_place_stories:
                extra_pics = [photo.image.url for photo in story.photos.all()[:3]]
                story_dto = SamePlaceStoryDto(
                    id=story.id,
                    title=story.title,
                    place_name=story.place.place_name,
                    preview=story.preview,
                    writer=story.writer,
                    writer_is_verified=story.writer.is_verified,
                    nickname=story.writer.nickname,
                    created=story.created,
                    rep_pic=story.rep_pic.url,
                    extra_pics=extra_pics,
                )
                story_dtos.append(story_dto)

        return story_dtos
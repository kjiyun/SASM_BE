import io
import time
import uuid

from django.conf import settings
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from rest_framework import exceptions
from django.shortcuts import get_object_or_404

from users.models import User
from stories.models import Story, StoryComment
from places.models import Place
from .selectors import StoryLikeSelector, StoryCommentSelector, semi_category

def check_user(user: User):
    if user.is_authenticated: 
        pass
    else:
        raise exceptions.ValidationError()


class StoryCoordinatorService:
    def __init__(self, user: User):
        self.user = user

    def like_or_dislike(self, story_id: int) -> bool:
        check_user(self.user)
        if StoryLikeSelector.likes(story_id=story_id, user=self.user):
            # Story의 like_cnt 1 감소
            StoryService.dislike(story_id=story_id, user=self.user)
            return False
        else:
            # Story의 like_cnt 1 증가
            StoryService.like(story_id=story_id, user=self.user)
            return True

    @transaction.atomic
    def create(self, 
               title: str, 
               writer_id: int,
               writer_sdp_admin: bool,
               place_id: int, 
               preview: str, 
               tag: str, 
               story_review: str, 
               html_content: str, 
               rep_pic: InMemoryUploadedFile, 
               category: str,
               semi_category: str) -> Story:
        print('coordinate')
        writer = User.objects.get(id__exact=writer_id)
        place = Place.objects.get(id__exact=place_id)

        service = StoryService()
        # semi_category = semi_category
        story = service.create(
            title=title,
            writer=writer,
            writer_sdp_admin=writer_sdp_admin,
            place=place,
            preview=preview,
            tag=tag,
            story_review=story_review,
            html_content=html_content,
            rep_pic=rep_pic,
            category=category,
            semi_category=semi_category,
        )

        return story

    @transaction.atomic
    def update(self, 
               story_id: int, 
               title: str, 
               place: Place, 
               story_review: str, 
               tag: str, 
               preview: str, 
               html_content: str, 
               rep_pic: InMemoryUploadedFile, 
               category: str, 
               semi_category: str) -> Story:
        service = StoryService()

        story = service.update(
            story_id=story_id,
            title=title,
            place=place,
            story_review=story_review,
            tag=tag,
            preview=preview,
            html_content=html_content,
            rep_pic=rep_pic,
            category=category,
            semi_category=semi_category,
        )

        return story
    
    @transaction.atomic
    def delete(self, story_id: int):
        service = StoryService()

        service.delete(story_id=story_id)


class StoryService:
    def __init__(self):
        pass

    @staticmethod
    def like(story_id: int, user: User):
        story = Story.objects.get(id=story_id)

        story.story_likeuser_set.add(user)
        story.story_like_cnt += 1

        story.full_clean()
        story.save()

    @staticmethod
    def dislike(story_id: int, user: User):
        story = Story.objects.get(id=story_id)

        story.story_likeuser_set.remove(user)
        story.story_like_cnt -= 1

        story.full_clean()
        story.save()

    def create(self,
               title: str, 
               writer: User,
               writer_sdp_admin: bool,
               place: Place, 
               preview: str, 
               tag: str, 
               story_review: str, 
               html_content: str, 
               rep_pic: InMemoryUploadedFile, 
               category: str,
               semi_category: str) -> Story:
        print('ll')
        # print('title:', title, writer, writer_is_verified, place, preview, tag, story_review, html_content, rep_pic, category, semi_category)
        story= Story(
            title=title,
            writer=writer,
            # writer__sdp_admin=writer_sdp_admin,
            place=place,
            preview=preview,
            tag=tag,
            story_review=story_review,
            html_content=html_content,
            rep_pic=rep_pic,
            place__category=category,
            semi_category=semi_category
        )
        print('ok')
        story.full_clean()
        story.save()

        return story
    
    def update(self,
               story_id: int,
               title: str, 
               place: Place, 
               preview: str, 
               tag: str, 
               story_review: str, 
               html_content: str, 
               rep_pic: InMemoryUploadedFile, 
               category: str,
               semi_category: str) -> Story:
        story = Story.objects.get(id=story_id)

        update_story = story(
            title=title,
            place=place,
            story_review=story_review,
            tag=tag,
            preview=preview,
            html_content=html_content,
            rep_pic=rep_pic,
            category=category,
            semi_category=semi_category,
        )

        return update_story
    
    @staticmethod
    def delete(self, story_id: int):
        story = Story.objects.get(id=story_id)

        story.delete()
    

class StoryCommentCoordinatorService:
    def __init__(self, user: User):
        self.user = user

    @transaction.atomic
    def create(self, story_id: int, content: str, mentioned_email: str = '') -> StoryComment:
        story = Story.objects.get(id=story_id)

        comment_service = StoryCommentService()

        if mentioned_email:
            mentioned_user = User.objects.get(email=mentioned_email)
        else:
            mentioned_user = None

        story_comment = comment_service.create(
            story=story,
            content=content,
            mentioned_user=mentioned_user,
            writer=self.user
        )

        return story_comment
    
    @transaction.atomic
    def update(self, story_comment_id: int, content: str, mentioned_email: str) -> StoryComment:
        story_comment_service = StoryCommentService()
        story_comment_selector = StoryCommentSelector()
        # user가 해당 story_comment의 writer가 아닐 경우 에러 발생
        if not story_comment_selector.isWriter(story_comment_id=story_comment_id, user=self.user):
            raise exceptions.ValidationError({'error': '댓글 작성자가 아닙니다.'})

        if mentioned_email:
            mentioned_user = User.objects.get(email=mentioned_email)
        else:
            mentioned_user = None

        story_comment = story_comment_service.update(
            story_comment_id=story_comment_id,
            content=content,
            mentioned_user=mentioned_user,
        )
        return story_comment
    
    @transaction.atomic
    def delete(self, story_comment_id: int):
        story_comment_service = StoryCommentService()
        story_comment_selector = StoryCommentSelector()

        # user가 해당 story_comment의 writer가 아닐 경우 에러 발생  
        if not story_comment_selector.isWriter(story_comment_id=story_comment_id, user=self.user):
            raise exceptions.ValidationError({'error': '댓글 작성자가 아닙니다.'})

        story_comment_service.delete(story_comment_id=story_comment_id)


class StoryCommentService:
    def __init__(self):
        pass

    def create(self, story: Story, content: str, mentioned_user: User, writer: User) -> StoryComment:
        story_comment = StoryComment(
            story=story,
            content=content,
            mention=mentioned_user,
            writer=writer,
        )

        story_comment.full_clean()
        story_comment.save()

        return story_comment
    

    def update(self, story_comment_id: int, content: str, mentioned_user: User) -> StoryComment:
        story_comment = StoryComment.objects.get(id=story_comment_id)
        story_comment.content = content
        story_comment.mention = mentioned_user

        story_comment.full_clean()
        story_comment.save()

        return story_comment
    
    def delete(self, story_comment_id: int):
        story_comment = StoryComment.objects.get(id=story_comment_id)
        story_comment.delete()

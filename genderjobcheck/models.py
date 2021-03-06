import re
import os
from binascii import hexlify
import wordlists
import logging

from django.db import models
from django.db.models import fields


class JobAd(models.Model):
    hash = models.CharField(max_length=16, unique=True)
    text = models.TextField()
    date = models.DateField(auto_now_add=True)
    masculine_coded_words = models.TextField(blank=True)
    feminine_coded_words = models.TextField(blank=True)

    possible_codings = (
        ("strongly feminine-coded", "strongly feminine-coded"),
        ("feminine-coded", "feminine-coded"),
        ("neutral", "neutral"),
        ("masculine-coded", "masculine-coded"),
        ("strongly masculine-coded", "strongly masculine-coded")
    )

    coding = models.CharField(max_length=24, blank=True,
        choices=possible_codings)

    @classmethod
    def create(cls, ad_text):
        job_ad = cls()
        job_ad.text = ad_text
        job_ad.make_hash()
        job_ad.save()
        job_ad.assess()
        job_ad.save()
        return job_ad

    def make_hash(self):
        while True:
            hash = hexlify(os.urandom(8))
            if hash not in [ad.hash for ad in JobAd.objects.all()]:
                self.hash = hash
                break

    def assess(self):
            ad_text = ''.join([i if ord(i) < 128 else ' ' for i in self.text])
            ad_text = re.sub("[\\s]", " ", ad_text, 0, 0)
            ad_text = re.sub("[\.\t\,\:;\(\)\.]", "", ad_text, 0, 0).split(" ")
            ad_text = [ad for ad in ad_text if ad != ""]

            masculine_coded_words = [adword for adword in ad_text
                for word in wordlists.masculine_coded_words
                if adword.startswith(word)]
            self.masculine_coded_words = (",").join(masculine_coded_words)

            feminine_coded_words = [adword for adword in ad_text
                for word in wordlists.feminine_coded_words
                if adword.startswith(word)]
            self.feminine_coded_words = (",").join(feminine_coded_words)

            if len(feminine_coded_words) > 2 and not masculine_coded_words:
                self.coding = "strongly feminine-coded"
            elif feminine_coded_words and not masculine_coded_words:
                self.coding = "feminine-coded"
            elif len(masculine_coded_words) > 2 and not feminine_coded_words:
                self.coding = "strongly masculine-coded"
            elif masculine_coded_words and not feminine_coded_words:
                self.coding = "masculine-coded"
            elif not masculine_coded_words and not feminine_coded_words:
                self.coding = "neutral"
            else:
                if len(feminine_coded_words) == len(masculine_coded_words):
                    self.coding = "neutral"
                if ((len(feminine_coded_words) / len(masculine_coded_words)) >=
                        2 and len(feminine_coded_words) > 5):
                    self.coding = "strongly feminine-coded"
                if ((len(masculine_coded_words) / len(feminine_coded_words)) >=
                        2 and len(masculine_coded_words) > 5):
                    self.coding = "strongly masculine-coded"
                if len(feminine_coded_words) > len(masculine_coded_words):
                    self.coding = "feminine-coded"
                if len(masculine_coded_words) > len(feminine_coded_words):
                    self.coding = "masculine-coded"

    def results_dictionary(self):
        results_dict = {"job_ad": self}
        if self.masculine_coded_words:
            results_dict["masculine_coded_words"] = self.masculine_coded_words.split(",")
        if self.feminine_coded_words:
            results_dict["feminine_coded_words"] = self.feminine_coded_words.split(",")

        if "feminine" in self.coding:
            results_dict["explanation"] = ("This job ad uses more words that "
                "are stereotypically feminine than words that are "
                "stereotypically masculine. Fortunately, the research "
                "suggests this will have only a slight effect on how "
                "appealing the job is to men, and will encourage women "
                "applicants.")
        elif "masculine" in self.coding:
            results_dict["explanation"] = ("This job ad uses more words that "
                "are stereotypically masculine than words that are "
                "stereotypically feminine. It risks putting women off "
                "applying, but will probably encourage men to apply.")
        elif not self.masculine_coded_words and not self.feminine_coded_words:
            results_dict["explanation"] = ("This job ad doesn't use any words "
                "that are stereotypically masculine and stereotypically "
                "feminine. It probably won't be off-putting to men or women "
                "applicants.")
        else:
            results_dict["explanation"] = ("This job ad uses an equal number "
                "of words that are stereotypically masculine and "
                "stereotypically feminine. It probably won't be off-putting "
                "to men or women applicants.")

        return results_dict

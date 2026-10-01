"""
Loads the draft message bank (148 messages) and the three Standard plans,
as sent to leadership for approval. Administrators can change any message
in Admin afterwards. Skipped if the bank already has messages.
"""
from django.db import migrations

BANK = [
[
"newcomers",
"Welcome",
1,
"",
"",
"Thank you for worshipping with us at Deeper Christian Life Ministry Bahrain. What did you enjoy most? If you'd rather not receive these messages, just let me know."
],
[
"newcomers",
"Welcome",
2,
"",
"",
"It was lovely to meet you. I'm [Shepherd], and I'll keep in touch. Is this the best number for you?"
],
[
"newcomers",
"Welcome",
3,
"I was glad when they said unto me, Let us go into the house of the LORD.",
"Psalm 122:1",
"You are always welcome in God's house. Will we see you again soon?"
],
[
"newcomers",
"Welcome",
4,
"",
"",
"How has your week been? Is there anything we can help with?"
],
[
"newcomers",
"Welcome",
5,
"Wherefore receive ye one another, as Christ also received us to the glory of God.",
"Romans 15:7",
"You are part of our family now. Would you like to meet a few more people from church?"
],
[
"newcomers",
"Welcome",
6,
"",
"",
"We pray this week brings you peace and joy. How are you and your family doing?"
],
[
"newcomers",
"Welcome",
7,
"The LORD bless thee, and keep thee",
"Numbers 6:24",
"Have a wonderful week. Is there anything we can pray about for you?"
],
[
"newcomers",
"Love of God",
1,
"Yea, I have loved thee with an everlasting love",
"Jeremiah 31:3",
"God's love for you does not change. What does that mean to you today?"
],
[
"newcomers",
"Love of God",
2,
"For God so loved the world, that he gave his only begotten Son",
"John 3:16",
"That love includes you. Would you like to talk more about it?"
],
[
"newcomers",
"Love of God",
3,
"But God commendeth his love toward us, in that, while we were yet sinners, Christ died for us.",
"Romans 5:8",
"You are loved just as you are. Is there anything I can pray about with you?"
],
[
"newcomers",
"Love of God",
4,
"We love him, because he first loved us.",
"1 John 4:19",
"May you feel His love today. How can we pray for you this week?"
],
[
"newcomers",
"Love of God",
5,
"It is of the LORD's mercies that we are not consumed, because his compassions fail not. They are new every morning",
"Lamentations 3:22-23",
"A fresh start is yours today. What would you like God to renew in your life?"
],
[
"newcomers",
"Love of God",
6,
"Since thou wast precious in my sight, thou hast been honourable, and I have loved thee",
"Isaiah 43:4",
"You are precious to God. May I share more about that with you?"
],
[
"newcomers",
"Love of God",
7,
"he will rejoice over thee with joy",
"Zephaniah 3:17",
"God delights in you. What has made you smile this week?"
],
[
"newcomers",
"Encouragement",
1,
"I can do all things through Christ which strengtheneth me.",
"Philippians 4:13",
"Whatever today brings, He is with you. What is on your plate this week?"
],
[
"newcomers",
"Encouragement",
2,
"the LORD thy God is with thee whithersoever thou goest.",
"Joshua 1:9",
"You are never alone. Is there something you are facing that we can pray about?"
],
[
"newcomers",
"Encouragement",
3,
"But they that wait upon the LORD shall renew their strength",
"Isaiah 40:31",
"May you find fresh strength this week. How are you holding up?"
],
[
"newcomers",
"Encouragement",
4,
"For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end.",
"Jeremiah 29:11",
"God has good plans for you. What are you hoping for this year?"
],
[
"newcomers",
"Encouragement",
5,
"This is the day which the LORD hath made",
"Psalm 118:24",
"Have a joyful day. What are you thankful for today?"
],
[
"newcomers",
"Encouragement",
6,
"Trust in the LORD with all thine heart",
"Proverbs 3:5",
"He will guide your steps. Is there a decision we can pray about with you?"
],
[
"newcomers",
"Encouragement",
7,
"he which hath begun a good work in you will perform it until the day of Jesus Christ",
"Philippians 1:6",
"Keep going. He is not finished with you. How can we support you?"
],
[
"newcomers",
"Encouragement",
8,
"for the joy of the LORD is your strength.",
"Nehemiah 8:10",
"Be encouraged today. What gives you joy?"
],
[
"newcomers",
"Salvation",
1,
"I am the way, the truth, and the life: no man cometh unto the Father, but by me.",
"John 14:6",
"Would you like to talk about knowing Jesus personally?"
],
[
"newcomers",
"Salvation",
2,
"Behold, I stand at the door, and knock",
"Revelation 3:20",
"Jesus is inviting you into a relationship with Him. Would you like to know what that means?"
],
[
"newcomers",
"Salvation",
3,
"That if thou shalt confess with thy mouth the Lord Jesus, and shalt believe in thine heart that God hath raised him from the dead, thou shalt be saved.",
"Romans 10:9",
"Salvation is a gift you can receive. Would you like to talk about it?"
],
[
"newcomers",
"Salvation",
4,
"Therefore if any man be in Christ, he is a new creature",
"2 Corinthians 5:17",
"A new beginning is possible. Would you like to hear how?"
],
[
"newcomers",
"Salvation",
5,
"If we confess our sins, he is faithful and just to forgive us our sins, and to cleanse us from all unrighteousness.",
"1 John 1:9",
"God's forgiveness is full and free. Do you have any questions about it?"
],
[
"newcomers",
"Salvation",
6,
"Believe on the Lord Jesus Christ, and thou shalt be saved",
"Acts 16:31",
"I would be happy to pray with you about this. Would that help?"
],
[
"newcomers",
"Salvation",
7,
"the gift of God is eternal life through Jesus Christ our Lord.",
"Romans 6:23",
"It is a gift, freely given. Have you received it?"
],
[
"newcomers",
"Challenges",
1,
"Cast thy burden upon the LORD, and he shall sustain thee",
"Psalm 55:22",
"You don't have to carry it alone. May I pray with you?"
],
[
"newcomers",
"Challenges",
2,
"God is our refuge and strength, a very present help in trouble.",
"Psalm 46:1",
"He is near when life is hard. How are things with you?"
],
[
"newcomers",
"Challenges",
3,
"Come unto me, all ye that labour and are heavy laden, and I will give you rest.",
"Matthew 11:28",
"Take a moment to rest in Him today. What is weighing on you?"
],
[
"newcomers",
"Challenges",
4,
"My grace is sufficient for thee: for my strength is made perfect in weakness.",
"2 Corinthians 12:9",
"His grace is enough for today. How can we help?"
],
[
"newcomers",
"Challenges",
5,
"And we know that all things work together for good to them that love God",
"Romans 8:28",
"God is at work in every situation. Is there one we can pray about?"
],
[
"newcomers",
"Challenges",
6,
"When thou passest through the waters, I will be with thee",
"Isaiah 43:2",
"Whatever you are going through, He is with you. Would you like to talk?"
],
[
"newcomers",
"Challenges",
7,
"The LORD is nigh unto them that are of a broken heart",
"Psalm 34:18",
"If your heart is heavy, we are here. Shall we pray together?"
],
[
"newcomers",
"Prayer",
1,
"",
"",
"What can we pray about with you this week?"
],
[
"newcomers",
"Prayer",
2,
"Call unto me, and I will answer thee, and shew thee great and mighty things, which thou knowest not.",
"Jeremiah 33:3",
"God hears every prayer. What would you like to bring to Him?"
],
[
"newcomers",
"Prayer",
3,
"The effectual fervent prayer of a righteous man availeth much.",
"James 5:16",
"We are praying for you this week. Is there anything specific?"
],
[
"newcomers",
"Prayer",
4,
"For where two or three are gathered together in my name, there am I in the midst of them.",
"Matthew 18:20",
"Would you like to join us for prayer this week?"
],
[
"newcomers",
"Prayer",
5,
"Pray without ceasing.",
"1 Thessalonians 5:17",
"Talk to God about everything today. Would you like a simple way to start?"
],
[
"newcomers",
"Prayer",
6,
"The LORD is nigh unto all them that call upon him",
"Psalm 145:18",
"He is only a prayer away. What is on your heart today?"
],
[
"newcomers",
"Prayer",
7,
"What things soever ye desire, when ye pray, believe that ye receive them, and ye shall have them.",
"Mark 11:24",
"Keep believing as you pray. What are you trusting God for?"
],
[
"newcomers",
"Invitation",
1,
"",
"",
"We would love to see you again. Our next service is [Next service]. Will you be able to come?"
],
[
"newcomers",
"Invitation",
2,
"Not forsaking the assembling of ourselves together",
"Hebrews 10:25",
"There is a place for you with us. Our next service is [Next service]. Shall I look out for you?"
],
[
"newcomers",
"Invitation",
3,
"Behold, how good and how pleasant it is for brethren to dwell together in unity!",
"Psalm 133:1",
"Come and share fellowship with us. Would you like to bring a friend?"
],
[
"newcomers",
"Invitation",
4,
"",
"",
"We also meet during the week for Bible study. Would you like the details?"
],
[
"newcomers",
"Invitation",
5,
"Enter into his gates with thanksgiving, and into his courts with praise",
"Psalm 100:4",
"We look forward to worshipping with you. Is there anything that would make your next visit easier?"
],
[
"newcomers",
"Invitation",
6,
"Let the word of Christ dwell in you richly",
"Colossians 3:16",
"Join us to study God's Word together. Shall I send you the details?"
],
[
"newcomers",
"Invitation",
7,
"",
"",
"There is a house fellowship near you where you can meet others from church. Would you like me to connect you?"
],
[
"newcomers",
"Belonging",
1,
"",
"",
"It's lovely to see you coming regularly! Would you like to join a house fellowship near you?"
],
[
"newcomers",
"Belonging",
2,
"And they continued stedfastly in the apostles' doctrine and fellowship",
"Acts 2:42",
"Growing together matters. Would you like to join our Bible study this week?"
],
[
"newcomers",
"Belonging",
3,
"",
"",
"Many people find their place by serving. Is there an area you would enjoy helping with?"
],
[
"newcomers",
"Belonging",
4,
"",
"",
"Would you like to learn about becoming a member of the church?"
],
[
"newcomers",
"Belonging",
5,
"Now ye are the body of Christ, and members in particular.",
"1 Corinthians 12:27",
"You have a place in this family. How are you settling in?"
],
[
"newcomers",
"Belonging",
6,
"",
"",
"Our pastor would love to meet you. Would you like to arrange a short visit?"
],
[
"newcomers",
"Belonging",
7,
"",
"",
"Would you like to join the Discipleship Class to grow in your faith?"
],
[
"newcomers",
"Belonging",
8,
"Those that be planted in the house of the LORD shall flourish in the courts of our God.",
"Psalm 92:13",
"May you flourish here. What would help you grow?"
],
[
"newcomers",
"Belonging",
9,
"",
"",
"Is there a friend or family member you would like to bring along one day?"
],
[
"newcomers",
"Belonging",
10,
"",
"",
"We would love to hear your story. Would you share how you found us?"
],
[
"converts",
"Assurance",
1,
"",
"",
"Welcome to God's family! Giving your life to Christ is the most important decision you will ever make, and I am here to walk with you. May we stay in touch as you grow in your faith?"
],
[
"converts",
"Assurance",
2,
"And I give unto them eternal life, and they shall never perish, neither shall any man pluck them out of my hand.",
"John 10:28",
"You are safe in His hands. How are you feeling since your decision?"
],
[
"converts",
"Assurance",
3,
"that ye may know that ye have eternal life",
"1 John 5:13",
"You can be sure of your salvation. Do you have any questions about it?"
],
[
"converts",
"Assurance",
4,
"There is therefore now no condemnation to them which are in Christ Jesus",
"Romans 8:1",
"Your past is forgiven. Is anything still troubling you?"
],
[
"converts",
"Assurance",
5,
"But as many as received him, to them gave he power to become the sons of God",
"John 1:12",
"You are a child of God. What does that mean to you?"
],
[
"converts",
"Assurance",
6,
"For by grace are ye saved through faith",
"Ephesians 2:8",
"Salvation is God's gift to you. Shall we thank Him together?"
],
[
"converts",
"Assurance",
7,
"Therefore if any man be in Christ, he is a new creature",
"2 Corinthians 5:17",
"Look how far you have come. What has God changed in you?"
],
[
"converts",
"The Word",
1,
"As newborn babes, desire the sincere milk of the word, that ye may grow thereby",
"1 Peter 2:2",
"Try reading one chapter of John's Gospel each day. Do you have a Bible?"
],
[
"converts",
"The Word",
2,
"Thy word is a lamp unto my feet, and a light unto my path.",
"Psalm 119:105",
"Let God's Word guide your steps. What did you read this week?"
],
[
"converts",
"The Word",
3,
"Thy word have I hid in mine heart, that I might not sin against thee.",
"Psalm 119:11",
"Why not learn this verse by heart? Shall I send you another one next week?"
],
[
"converts",
"The Word",
4,
"This book of the law shall not depart out of thy mouth",
"Joshua 1:8",
"A little of God's Word every day makes a big difference. When is the best time for you to read?"
],
[
"converts",
"The Word",
5,
"All scripture is given by inspiration of God, and is profitable for doctrine, for reproof, for correction, for instruction in righteousness",
"2 Timothy 3:16",
"Is there anything in the Bible you would like me to explain?"
],
[
"converts",
"The Word",
6,
"Man shall not live by bread alone, but by every word that proceedeth out of the mouth of God.",
"Matthew 4:4",
"Feed your spirit today. Which verse has spoken to you lately?"
],
[
"converts",
"Prayer",
1,
"",
"",
"Would you like us to pray together this week? When suits you?"
],
[
"converts",
"Prayer",
2,
"Draw nigh to God, and he will draw nigh to you.",
"James 4:8",
"Take a few quiet minutes with God today. How is your prayer time going?"
],
[
"converts",
"Prayer",
3,
"My voice shalt thou hear in the morning, O LORD",
"Psalm 5:3",
"Start your day by talking to Him. Would you like a simple way to pray?"
],
[
"converts",
"Prayer",
4,
"And this is the confidence that we have in him, that, if we ask any thing according to his will, he heareth us",
"1 John 5:14",
"He hears you when you pray. What would you like to ask Him?"
],
[
"converts",
"Prayer",
5,
"men ought always to pray, and not to faint",
"Luke 18:1",
"Keep praying, even when answers take time. What are you praying about?"
],
[
"converts",
"Prayer",
6,
"pray to thy Father which is in secret",
"Matthew 6:6",
"Find a quiet place to meet with God. Where could that be for you?"
],
[
"converts",
"Holiness",
1,
"For this is the will of God, even your sanctification",
"1 Thessalonians 4:3",
"God wants to make you holy, and He will help you. Is there an area you'd like prayer for?"
],
[
"converts",
"Holiness",
2,
"Create in me a clean heart, O God, and renew a right spirit within me.",
"Psalm 51:10",
"A good prayer to pray today. Shall we pray it together?"
],
[
"converts",
"Holiness",
3,
"And be not conformed to this world: but be ye transformed by the renewing of your mind",
"Romans 12:2",
"Let God change how you think. What is He teaching you?"
],
[
"converts",
"Holiness",
4,
"This I say then, Walk in the Spirit, and ye shall not fulfil the lust of the flesh.",
"Galatians 5:16",
"He gives strength to live a new life. What is your biggest challenge right now?"
],
[
"converts",
"Holiness",
5,
"Follow peace with all men, and holiness, without which no man shall see the Lord",
"Hebrews 12:14",
"Holiness is the path He walks with you. Would you like to talk about it?"
],
[
"converts",
"Holiness",
6,
"But if we walk in the light, as he is in the light, we have fellowship one with another, and the blood of Jesus Christ his Son cleanseth us from all sin.",
"1 John 1:7",
"His blood cleanses you completely. How can I pray for you?"
],
[
"converts",
"Baptism",
1,
"Go ye therefore, and teach all nations, baptizing them in the name of the Father, and of the Son, and of the Holy Ghost",
"Matthew 28:19",
"Baptism is the next step of obedience. Would you like to join the baptism class?"
],
[
"converts",
"Baptism",
2,
"He that believeth and is baptized shall be saved",
"Mark 16:16",
"Would you like to know more about baptism?"
],
[
"converts",
"Baptism",
3,
"Therefore we are buried with him by baptism into death",
"Romans 6:4",
"Baptism shows the new life you now have. Shall I tell you when the next baptism is?"
],
[
"converts",
"Baptism",
4,
"Then Peter said unto them, Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins, and ye shall receive the gift of the Holy Ghost.",
"Acts 2:38",
"God has more for you. Do you have questions about this?"
],
[
"converts",
"Baptism",
5,
"But ye shall receive power, after that the Holy Ghost is come upon you",
"Acts 1:8",
"Shall we pray together for the baptism of the Holy Ghost?"
],
[
"converts",
"Fellowship",
1,
"And they continued stedfastly in the apostles' doctrine and fellowship",
"Acts 2:42",
"Growing together is part of God's plan. Will I see you at [Next service]?"
],
[
"converts",
"Fellowship",
2,
"And let us consider one another to provoke unto love and to good works",
"Hebrews 10:24",
"Your church family is here for you. Have you met others your age yet?"
],
[
"converts",
"Fellowship",
3,
"Iron sharpeneth iron",
"Proverbs 27:17",
"Would you like to join a house fellowship near you?"
],
[
"converts",
"Fellowship",
4,
"that ye also may have fellowship with us",
"1 John 1:3",
"You belong with us. How are you finding church so far?"
],
[
"converts",
"Fellowship",
5,
"Two are better than one",
"Ecclesiastes 4:9",
"Let's keep walking this road together. When shall we meet next?"
],
[
"converts",
"Sharing your faith",
1,
"Let your light so shine before men, that they may see your good works, and glorify your Father which is in heaven.",
"Matthew 5:16",
"Your changed life speaks to others. Has anyone noticed the change?"
],
[
"converts",
"Sharing your faith",
2,
"Go home to thy friends, and tell them how great things the Lord hath done for thee, and hath had compassion on thee.",
"Mark 5:19",
"Who could you share your story with this week?"
],
[
"converts",
"Sharing your faith",
3,
"For I am not ashamed of the gospel of Christ: for it is the power of God unto salvation to every one that believeth",
"Romans 1:16",
"The good news you received is for others too. Who comes to mind?"
],
[
"converts",
"Sharing your faith",
4,
"be ready always to give an answer to every man that asketh you a reason of the hope that is in you with meekness and fear",
"1 Peter 3:15",
"Shall we practise sharing your story together?"
],
[
"converts",
"Sharing your faith",
5,
"he that winneth souls is wise.",
"Proverbs 11:30",
"Who is one person you would love to see come to Christ?"
],
[
"online",
"First reply",
1,
"",
"",
"Thank you for getting in touch with Deeper Christian Life Ministry Bahrain. [Answer to their question] May we keep in touch?"
],
[
"online",
"First reply",
2,
"",
"",
"Thank you for your message. I have passed it to our pastor, who will reply to you personally. Is this the best way to reach you?"
],
[
"online",
"First reply",
3,
"",
"",
"Just checking you received our reply. Is there anything else you would like to know?"
],
[
"online",
"First reply",
4,
"",
"",
"It was good to hear from you. Is there anything we can pray about with you?"
],
[
"online",
"Invitation",
1,
"",
"",
"We would love to welcome you in person. Our next service is [Next service]. Would you like to come?"
],
[
"online",
"Invitation",
2,
"I was glad when they said unto me, Let us go into the house of the LORD.",
"Psalm 122:1",
"Our doors are open to you. When might you visit?"
],
[
"online",
"Invitation",
3,
"",
"",
"If it helps, I can meet you at the entrance on your first visit. When are you thinking of coming?"
],
[
"online",
"Invitation",
4,
"",
"",
"Many people first get to know us online. Whenever you are ready to visit, you are welcome. Is there anything you would like to know first?"
],
[
"online",
"Invitation",
5,
"",
"",
"Would you like our location on a map? I can send it here."
],
[
"online",
"What to expect",
1,
"",
"",
"Our service includes worship, prayer and teaching from the Bible. Come as you are. Any questions about the day?"
],
[
"online",
"What to expect",
2,
"",
"",
"Children and young people are welcome too. Would you be coming with family?"
],
[
"online",
"What to expect",
3,
"",
"",
"There is no need to bring anything. We will be happy to show you around. Shall I look out for you?"
],
[
"online",
"What to expect",
4,
"",
"",
"If you have questions about what we believe, I would be glad to talk. Is there anything on your mind?"
],
[
"online",
"Encouragement",
1,
"For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end.",
"Jeremiah 29:11",
"God has good plans for you. How are you doing today?"
],
[
"online",
"Encouragement",
2,
"Come unto me, all ye that labour and are heavy laden, and I will give you rest.",
"Matthew 11:28",
"Whatever you are carrying, He cares. Is there anything we can pray about?"
],
[
"online",
"Encouragement",
3,
"God is our refuge and strength, a very present help in trouble.",
"Psalm 46:1",
"He is near to you today. How can we help?"
],
[
"online",
"Encouragement",
4,
"For God so loved the world, that he gave his only begotten Son",
"John 3:16",
"That love includes you. Would you like to know more?"
],
[
"online",
"Staying connected",
1,
"",
"",
"You are also welcome to join our Bible study during the week. Would you like the details?"
],
[
"online",
"Staying connected",
2,
"",
"",
"Would you like me to send you a short word of encouragement from time to time?"
],
[
"online",
"Staying connected",
3,
"",
"",
"It has been a while. We are still here for you. How have you been?"
],
[
"any",
"Life moments",
1,
"In all thy ways acknowledge him, and he shall direct thy paths.",
"Proverbs 3:6",
"All the best in your exams. When are they, so we can pray?"
],
[
"any",
"Life moments",
2,
"Commit thy way unto the LORD",
"Psalm 37:5",
"Congratulations on the new job! How is it going so far?"
],
[
"any",
"Life moments",
3,
"But my God shall supply all your need according to his riches in glory by Christ Jesus.",
"Philippians 4:19",
"I'm sorry to hear about your job. How can we help and pray?"
],
[
"any",
"Life moments",
4,
"For I will restore health unto thee, and I will heal thee of thy wounds, saith the LORD",
"Jeremiah 30:17",
"We are praying for your recovery. How are you feeling today?"
],
[
"any",
"Life moments",
5,
"My help cometh from the LORD, which made heaven and earth.",
"Psalm 121:2",
"We are praying for you in hospital. Would you like a visit?"
],
[
"any",
"Life moments",
6,
"Blessed are they that mourn: for they shall be comforted.",
"Matthew 5:4",
"We are so sorry for your loss. Is there anything we can do for you and your family?"
],
[
"any",
"Life moments",
7,
"Lo, children are an heritage of the LORD",
"Psalm 127:3",
"Congratulations on your new baby! How are you all doing?"
],
[
"any",
"Life moments",
8,
"",
"",
"Happy birthday! May this year be full of God's blessings. How are you celebrating?"
],
[
"any",
"Life moments",
9,
"The LORD shall preserve thy going out and thy coming in from this time forth, and even for evermore.",
"Psalm 121:8",
"Safe travels! When are you back?"
],
[
"any",
"Life moments",
10,
"",
"",
"Congratulations on your wedding! May God bless your home. How was the day?"
],
[
"any",
"Life moments",
11,
"Casting all your care upon him",
"1 Peter 5:7",
"Whatever is worrying you, you can bring it to Him. Would you like to talk?"
],
[
"any",
"Life moments",
12,
"",
"",
"I hear you're moving house. Can we help in any way?"
],
[
"any",
"Life moments",
13,
"",
"",
"We missed you this week. Is everything alright?"
],
[
"any",
"Life moments",
14,
"",
"",
"Thank you for your help this week. It meant a lot. How did you find it?"
],
[
"any",
"Seasons",
1,
"Behold, I will do a new thing",
"Isaiah 43:19",
"Happy new year! What are you trusting God for this year?"
],
[
"any",
"Seasons",
2,
"But he was wounded for our transgressions, he was bruised for our iniquities",
"Isaiah 53:5",
"Remembering His love this Good Friday. Will you join us for our service?"
],
[
"any",
"Seasons",
3,
"He is not here: for he is risen, as he said.",
"Matthew 28:6",
"Happy Easter! Would you like to celebrate with us?"
],
[
"any",
"Seasons",
4,
"For unto you is born this day in the city of David a Saviour, which is Christ the Lord.",
"Luke 2:11",
"Merry Christmas! Would you like to join our Christmas service?"
],
[
"any",
"Seasons",
5,
"",
"",
"We have a special programme coming up, [Programme]. Would you like to come?"
],
[
"any",
"Seasons",
6,
"O give thanks unto the LORD, for he is good: for his mercy endureth for ever.",
"Psalm 107:1",
"As the year ends, what are you thankful for?"
],
[
"any",
"Seasons",
7,
"",
"",
"A new school year is starting. Can we pray for your family?"
],
[
"any",
"Seasons",
8,
"",
"",
"Wishing you a restful holiday. Will you be around for church?"
],
[
"any",
"Seasons",
9,
"",
"",
"It's a year since you first joined us! How has the year been for you?"
],
[
"any",
"Seasons",
10,
"",
"",
"Our church celebration is coming up, [Programme]. We would love you to be there. Can you make it?"
],
[
"any",
"Final gentle message",
1,
"",
"",
"We haven't seen you for a while, and that's fine. Our door is always open, and you can reach me here any time. God bless you."
],
[
"any",
"Final gentle message",
2,
"",
"",
"We won't keep messaging, but we're here whenever you'd like to visit or talk. God bless you."
],
[
"any",
"Final gentle message",
3,
"",
"",
"I'm always here for you as you keep growing in Christ. Reach out any time."
],
[
"any",
"Final gentle message",
4,
"",
"",
"Thank you for letting us stay in touch. You are always welcome with us."
]
]

PLANS = [["newcomers", 1, "newcomers", "Welcome", 1], ["newcomers", 3, "newcomers", "Welcome", 4], ["newcomers", 6, "newcomers", "Invitation", 1], ["newcomers", 9, "newcomers", "Love of God", 1], ["newcomers", 13, "newcomers", "Prayer", 1], ["newcomers", 16, "newcomers", "Encouragement", 1], ["newcomers", 20, "newcomers", "Invitation", 5], ["newcomers", 23, "newcomers", "Salvation", 1], ["newcomers", 27, "newcomers", "Welcome", 5], ["newcomers", 30, "newcomers", "Challenges", 1], ["newcomers", 34, "newcomers", "Invitation", 7], ["newcomers", 37, "newcomers", "Love of God", 4], ["newcomers", 41, "any", "Final gentle message", 1], ["converts", 1, "converts", "Assurance", 1], ["converts", 2, "converts", "Assurance", 2], ["converts", 3, "converts", "The Word", 1], ["converts", 4, "converts", "Prayer", 1], ["converts", 5, "converts", "Assurance", 3], ["converts", 6, "converts", "The Word", 2], ["converts", 7, "converts", "Baptism", 1], ["converts", 8, "converts", "Holiness", 1], ["converts", 9, "converts", "Prayer", 2], ["converts", 10, "converts", "The Word", 3], ["converts", 11, "converts", "Assurance", 4], ["converts", 12, "converts", "Fellowship", 1], ["converts", 13, "converts", "Sharing your faith", 1], ["converts", 14, "converts", "Fellowship", 2], ["converts", 16, "converts", "Holiness", 2], ["converts", 19, "converts", "The Word", 4], ["converts", 23, "converts", "Prayer", 3], ["converts", 26, "converts", "Baptism", 2], ["converts", 30, "converts", "Assurance", 5], ["converts", 33, "converts", "Holiness", 3], ["converts", 37, "converts", "Fellowship", 3], ["converts", 40, "converts", "The Word", 5], ["converts", 44, "converts", "Sharing your faith", 2], ["converts", 47, "converts", "Baptism", 3], ["converts", 51, "converts", "Prayer", 4], ["converts", 54, "converts", "Holiness", 4], ["converts", 58, "converts", "Assurance", 6], ["converts", 61, "converts", "The Word", 6], ["converts", 65, "converts", "Fellowship", 4], ["converts", 68, "converts", "Sharing your faith", 3], ["converts", 72, "converts", "Baptism", 4], ["converts", 75, "converts", "Holiness", 5], ["converts", 79, "converts", "Prayer", 5], ["converts", 82, "any", "Final gentle message", 3], ["online", 1, "online", "First reply", 1], ["online", 3, "online", "First reply", 3], ["online", 7, "online", "Invitation", 1], ["online", 14, "online", "What to expect", 1], ["online", 21, "online", "Encouragement", 1], ["online", 51, "online", "Invitation", 4], ["online", 81, "online", "Encouragement", 2], ["online", 111, "any", "Final gentle message", 2]]


def load(apps, schema_editor):
    T = apps.get_model("followup", "MessageTemplate")
    P = apps.get_model("followup", "PlanStep")
    if T.objects.exists():
        return
    made = {}
    for journey, theme, number, verse, reference, body in BANK:
        made[(journey, theme, number)] = T.objects.create(
            journey=journey, theme=theme, number=number, verse=verse, reference=reference, body=body)
    for journey, day, bank_journey, theme, number in PLANS:
        P.objects.create(journey=journey, day=day, template=made[(bank_journey, theme, number)])


def unload(apps, schema_editor):
    apps.get_model("followup", "PlanStep").objects.all().delete()
    apps.get_model("followup", "MessageTemplate").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("followup", "0001_initial")]
    operations = [migrations.RunPython(load, unload)]

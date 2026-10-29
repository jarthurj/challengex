"""Sentences from the FY2021 report's scanned pages that discuss a table or figure.

FY2021 chapter pages 9-69 (and Appendix B) are images with no text layer, so their sentences
can't be read programmatically. Each sentence below was located with OCR and then transcribed
by hand from the rendered page image, exactly as printed (spelling, punctuation, and the
report's own typos included). PDF page -> sentences in reading order.

`manage.py extract_context` treats these pages like text pages: every sentence that mentions a
table number becomes an excerpt for that table, labelled as transcribed from the page image.
"""

QUOTES = {
    9: [
        "As seen in Table E.1, in 2021 U.S. households received 104.2 billion pieces of mail and sent 7.1 billion pieces.",
        "Table E.2 shows household mail volumes by market for 2019 through 2021.",
    ],
    10: [
        "As Table E.3 indicates, over the last ten years the share of payments by mail plummeted, falling from 44% in 2011 to 19% in 2021, while online payments surged from 51% to 79%.",
        "As Table E.4 illustrates, 89% of advertising mail received by households consisted of Marketing Mail (59.2 billion commercial and non-profit pieces).",
    ],
    11: [
        "As shown in Table E.2, households received 3.6 billion periodicals by mail in 2021, a 6% decrease from 3.9 billion pieces received in 2020.",
        "According to Table E.5, magazines made up 70% of Periodicals delivered by mail and newspapers accounted for another 21%.",
        "In 2021 households received 6.4 billion packages and sent 0.7 billion pieces (see Table E.6).",
    ],
    14: [
        "Table 1.1 presents the RPW volumes for FY 2021, including FY 2020 and 2019.",
    ],
    15: [
        "Tables 1.2 and 1.3 show total volumes for each type of mail flow.",
        "Table 1.4 shows pieces per household per week for each flow.",
        "As shown in Table 1.3 above, domestic mail to and from households represented 84 percent of total FY 2021 mail volume; equating to 108.7 billion pieces sent and received by U.S. households.",
        "As Table 1.5 shows, households received 104.2 billion pieces of mail and sent 7.1 billion.",
    ],
    16: [
        "Table 1.6 presents these data in two other forms, annual volumes per household and pieces per household per week.",
        "Table 1.7 crosswalks between classes of mail and the markets they serve.",
    ],
    19: [
        "However, as Table 2.1 illustrates, from 2001 to 2021 average volume fell 2.3% annually.",
        "Referring to Table 2.1, the 1980s were a time of extraordinary mail volume growth (4.6% annually) that began in 1978 and continued through 1988.",
    ],
    20: [
        "Tables 2.2 and 2.3 illustrate how some households' demographic characteristics can drive mail usage more than others.",
        "Table 2.2 shows that households receiving less than 12 pieces of mail per week earned an average of $45,691 annually; by contrast, those receiving 36 to 44 pieces per week earned $99,512.",
        "Table 2.3, on the other hand, shows that mail volume was related to college graduates but not as clearly at lower levels of education.",
    ],
    21: [
        "As Table 2.4 shows, in 2021 the relationship between income and education was fairly consistent at each level of income.",
        "The relationship between income and age, shown in Table 2.5, is somewhat more complicated.",
    ],
    23: [
        "Households with three or more adults made up only 15% of the total (Table 2.6).",
        "When all household members are included (adults and children), households with three or more members made up 33% of all households (Table 2.7).",
        "Table 2.8 shows that 93% of US households have Internet access and almost all now have Broadband access.",
        "The highest levels of Internet and Broadband access are now in almost all households with incomes over $100,000 (each with 99%), as seen in Figure 2.1a.",
        "According to Figure 2.1b, age is also a determinant of households' Internet access.",
        "Figure 2.2 shows that number of Broadband subscribers has grown rapidly since the early 2000's.",
    ],
    25: [
        "Figure 2.3 shows that, despite a declining frequency of visits over the last ten years, the use of post offices for mailing services continues to dominate the mail service industry.",
    ],
    27: [
        "As seen in Table 3.1, in 2020 and 2021 correspondence volumes remained relatively flat.",
        "Table 3.1 also provides a sector breakdown of correspondence mail flows.",
    ],
    28: [
        "Tables 3.2 and 3.3 show that both household income and educational attainment have a strong influence on the volume of correspondence sent and received by households.",
    ],
    29: [
        "Tables 3.4 and 3.5 illustrate that age is a strong determinant of households' use of correspondence mail.",
    ],
    30: [
        "In Tables 3.6 and 3.7, the jump from one to two persons is associated with a considerable increase in correspondence mail use.",
        "In Table 3.7, however, we do see that increases in correspondence related to household size were generally driven by the presence of additional adults in the household.",
        "As illustrated in Table 3.8, households with Internet access received significantly more correspondence than households without such service.",
        "In Table 3.9, households with Internet access have substantially more income and education than those without a connection.",
        "With respect to correspondence mail sent by households, Table 3.8 does not indicate a clear impact of Internet access on volumes.",
    ],
    31: [
        "Table 3.10 details volumes by type of correspondence.",
    ],
    32: [
        "Figure 3.1 illustrates how the various categories of personal correspondence were impacted by income.",
        "In Figure 3.2, the number of greeting cards sent seems to follow a pattern where the number of greeting cards sent grows as the age of the head of household increases.",
    ],
    33: [
        "Figure 3.3 shows the effects of income and age on Holiday greeting cards sent over the last three-year period.",
    ],
    34: [
        "According to Table 3.1 above, correspondence received from the non-household sector was the main component of total correspondence sent and received by households, accounting for about 74% of the total volume.",
        "Table 3.12 presents changes in business correspondence by type and by sector.",
    ],
    35: [
        "In 2021 transaction mail sent and received accounted for 17% of all household mail (see Table E.2) and 48% of all First-Class Mail sent and received by households; as such, transactions represent a major component of the mail stream.",
        "As Table 4.1 illustrates, in 2021 total transaction mail sent and received by households fell 5.1% from 2020.",
        "As Table 4.1 illustrates, in 2021 bills and statements received by mail fell 7.4% and 7.5% respectively.",
        "In Table 4.1 we also see that, for each of the three years, the number of bills paid represented only about one-third of bills received.",
    ],
    36: [
        "As shown in Tables 4.2 and 4.3, household income had a strong influence on the volume of transaction mail received.",
        "As we look at transaction mail sent by households, neither income nor education seem to have a measurable impact on volumes (Table 4.3).",
    ],
    37: [
        "Tables 4.4 and 4.5 show that age has a greater influence on the volume of transaction mail sent and received than other demographic characteristics.",
    ],
    38: [
        "In terms of household size, Table 4.6 shows that an increase from a one-person household to two-person household adds 41% (0.7 pieces) more transaction mail received per week and 25% (0.1 pieces) more pieces of mail sent per week.",
        "With respect to transactions mail received, Table 4.7 shows that each additional adult adds almost one piece of mail received per week.",
        "As shown in Table 4.8, households with Internet access received more transaction mail than those without it.",
        "Lower income households, in many cases, do not have access to the Internet (see Table 4.9) and can only conduct transactions by mail.",
    ],
    39: [
        "Table 4.10 presents the number of bills paid monthly and other relevant statistics for each payment type.",
        "Table 4.10 also shows that in 2021 only 51% of households paid at least one bill by mail, a substantial decline from 68% in 2016.",
    ],
    40: [
        "As Figure 4.1 illustrates, electronic payments have accounted for a rapidly growing share of households' payments.",
        "As Figure 4.2 illustrates, between 2006 and 2021, these types of payments almost doubled, increasing 79%.",
    ],
    42: [
        "Table 4.11 shows an industry breakdown of bills and statements received by households.",
    ],
    43: [
        "Figures 4.5a and 4.5b, show number of bills and statements received in the mail, by household income.",
    ],
    45: [
        "Table 4.12 shows the number of monthly bills received by mail and online from 2019 through 2021.",
        "Figure 4.6 shows the shares of bills received either online or by mail for each age cohort.",
    ],
    47: [
        "As Table 5.1 illustrates, direct mail spending rose 12.8% from 2020.",
        "The large fluctuations from one year to the next in the \"Other\" category of spending (in Table 5.1) are the result of seasonality associated with spending on election and Olympic campaigns.",
        "According to GroupM's estimates, direct mail's share of total advertising spending began to decline aggressively in 2015, falling from 9% to 4.9% in 2021, the lowest level to-date (Fig 5.1).",
    ],
    48: [
        "Tables 5.2 and 5.3 show that in 2021 First-Class Mail advertising totaled 6.7 billion pieces, a 6.9% increase from 2020, representing 10% of total household ad mail received.",
    ],
    49: [
        "As illustrated in Table 5.4, the relationship between advertising mail and household income is quite strong.",
        "Table 5.4 also shows that education too played a key role in the volume of advertising mail received by households.",
    ],
    50: [
        "As Table 5.5 illustrates, households headed by an older person receive significantly more advertising mail than their younger counterparts at every income level.",
        "In Table 5.5 we see that, heads of household over 55 with incomes greater than $100,000 received 15.2 ad pieces per week, more than any other demographic combination.",
        "Tables 5.6 and 5.7 show that advertising mail received increased with the size and number of adults in the household.",
        "Table 5.6 shows that, while this is evident when looking at changes in household sizes from one to two household members (a 35% increase), additional members over two do not increase, and may in fact reduce the number of advertising pieces received.",
    ],
    51: [
        "In Table 5.7 we see that households with two adults received 33% more ad pieces than those with only one adult.",
        "In Table 5.8 we see households without Internet access received about the same number of ads as those with either Broadband or Dial-up service.",
    ],
    52: [
        "Figure 5.2 shows advertising mail volumes by major industry.",
        "In Figure 5.3 we see that, in 2021, 49% of households read ads received by mail, a percentage remarkably stable since 1987, when the Household Diary Study project first began.",
    ],
    53: [
        "As Figure 5.4 illustrates, catalogs attract considerably more attention than credit card ads, as they typically are more interesting to read.",
    ],
    54: [
        "Another interesting result can be seen in Figure 5.5. In some cases, household behavior toward advertising mail appears to depend on how much advertising mail they receive.",
        "However, Figure 5.5 also shows that, on average, more than 50% of households read all or some of the ads received, a percentage that, generally, is unaffected by the volume received.",
        "Figure 5.6 shows the effect of household demographics on ad mail reading rates.",
    ],
    55: [
        "Table 5.10 presents the intended response rates to advertising mail.",
        "For example, catalogs, which typically enjoy a high response rate (linked to the high read rate shown in Figure 5.4), are routinely mailed by Marketing Mail and only rarely by First-Class Mail.",
        "Credit card ads, on the other hand, have the lowest response rate (linked to the low read rate shown in Figure 5.4) and are often mailed First-Class.",
        "Figure 5.7 presents the total number of intended responses to advertising mail by income.",
        "As illustrated earlier in Tables 5.4 and 5.5, higher-income households received more advertising mail compared to other income groups.",
        "Figure 5.7 combines the weekly volume of advertising mail received by household income with the respective intended response rates reported in Table 5.10.",
    ],
    56: [
        "While intended responses do not always lead to actual responses, the data presented in Table 5.10 and Figure 5.7 help explain why direct mail is a popular choice of advertisers in the U.S.",
        "Read rates and intended response rates for mail advertising, on the other hand, have been much higher, averaging about 50 percent (see Figure 5.3) and 10%, respectively.",
    ],
    59: [
        "As shown in Table E.2 of the Executive Summary, periodicals represented 3.3% of total household mail.",
        "Table E.2 also shows that periodicals fell 14% over the last 3 years, from 4.2 billion pieces in 2019 to 3.6 billion pieces in 2021.",
        "Table 6.1 provides a more detail view of volumes, with a breakdown by type of periodicals households received.",
        "As Figure 6.3 illustrates, newspaper circulation fell 61% from 1990 to 2020 (data are not yet available after 2021).",
    ],
    60: [
        "Table 6.2 illustrates that the number of periodicals received by households increased only when earnings increased from less than $35K to the $35K-$65K range and again when earnings were greater than $100K, However, within the wider income range from 35K to $100K, the number of periodicals remained unchanged.",
        "Table 6.3 shows that the number of periodicals received by households increased with the age of heads of household.",
    ],
    61: [
        "Table 6.4 and Table 6.5 show that as households increased in size from one to two persons, the number of periodicals increased 75%.",
        "In Table 6.6 we see that households with Internet access received 29% fewer periodicals through the mail than those without access.",
    ],
    62: [
        "Figure 6.4 provides an overview of subscription types for periodicals received by mail in FYs 2021, 2020, and 2010.",
        "Examining periodical volumes by sender type, Table 6.7 shows that households received most periodicals (74%) from commercial organizations.",
    ],
    63: [
        "Figure 6.5 presents a long-term view of the relationship between households' income and the number of periodicals received.",
    ],
    65: [
        "Survey findings show that high-income households received significantly more packages than their less affluent counterparts (see Fig. 7.1).",
        "As shown in Table 7.1, heads of household between 35 and 54 years of age received more packages than either the younger or older age cohorts.",
        "Looking at Table 7.2, the number of packages sent was lowest for households under 35 but there were no other significant changes at ages 35 and over.",
    ],
    66: [
        "Tables 7.3 and 7.4 illustrate the impact of education on the number of packages received and sent by households.",
        "The survey found that the relationship between packages sent and education was very similar to the one observed for packages received (Table 7.4).",
    ],
    67: [
        "As would be expected, Table 7.5 shows that two-person households received and sent significantly more packages than one-person households.",
        "In Table 7.6 we see that households with two or more adults received more packages than those with one adult.",
        "In Table 7.7, households with Broadband access sent 60% more and received twice as many packages as households without access.",
        "Relatedly, Table 7.8 shows that online-shoppers received and sent more than twice as many packages as households that did not shop online.",
    ],
    68: [
        "As shown in Table 7.9, more than one-quarter of packages received by households (27%) contained clothing items.",
    ],
    90: [
        "Table B.2 below shows the distribution of recruited households by recruitment type.",
    ],
    95: [
        "Table B.9 provides unweighted sample counts from FY 2021 recruitment data for strata:",
        "Table B.10 provides unweighted sample counts from FY 2021 recruitment data for region.",
        "Table B.11 indicates the distribution of households from the FY 2021 recruitment sample within strata and regions.",
        "As Table B.12 shows, each county was grouped according to its location within these 12 mutually exclusive and collectively exhaustive geographic categories.",
        "Geography weights appear in the last column to the right in Table B.12.",
    ],
}

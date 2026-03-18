<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:mei="http://www.music-encoding.org/ns/mei"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

  <xsl:output indent="yes"/>
  <xsl:param name="title" select="''"/>
  <xsl:param name="siglum" select="''" />

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="mei:fileDesc">
    <fileDesc>
            <titleStmt>
                <title><xsl:value-of select="$title"/></title>
            </titleStmt>
            <editionStmt>
                <edition>
                    <identifier type="siglum"><xsl:value-of select="$siglum"/></identifier>
                </edition>
            </editionStmt>
            <pubStmt/>
        </fileDesc>
  </xsl:template>
</xsl:stylesheet>
